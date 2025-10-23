import os
import io
from math import ceil
from typing import Optional
from PIL import Image, ImageOps, ImageChops
from loguru import logger


class MediaOptimizer:
    def __init__(
        self,
        max_size_kb=100,
        optimize_png=True,
        optimize_jpg=True,
        min_side_px=64,
        scale_step=0.02,
        max_compression_jpg=85,
        max_compression_png=9,  # kept for API compatibility; unused in PNG path below
        convert_png_to_jpg=True,
        emit_resized_png=True,
        jpg_suffix="",
        png_suffix="",
    ):
        """
        :param max_size_kb: Size cap per output (KB) for optimization targets.
        :param optimize_png: Whether to process .png inputs at all.
        :param optimize_jpg: Whether to optimize .jpg/.jpeg inputs.
        :param min_side_px: Minimum dimension when downscaling.
        :param scale_step: Fraction to reduce width/height each iteration (e.g. 0.02 = 2%).
        :param max_compression_jpg: Lowest JPEG quality we’ll try (e.g. 85).
        :param max_compression_png: Kept for compatibility; PNG path below avoids _encode_png.
        :param convert_png_to_jpg: For PNG inputs, also write an optimized JPEG sibling.
        :param emit_resized_png: For PNG inputs, also write a resized PNG sibling (no _encode_png).
        :param jpg_suffix: Suffix for converted JPG (before extension).
        :param png_suffix: Suffix for resized PNG (before extension).
        """
        self.max_size = max_size_kb * 1024
        self.optimize_png = optimize_png
        self.optimize_jpg = optimize_jpg
        self.min_side_px = int(min_side_px)
        self.scale_step = float(scale_step)
        self.max_compression_jpg = int(max_compression_jpg)
        self.max_compression_png = int(max_compression_png)
        self.convert_png_to_jpg = bool(convert_png_to_jpg)
        self.emit_resized_png = bool(emit_resized_png)
        self.jpg_suffix = str(jpg_suffix)
        self.png_suffix = str(png_suffix)

        # JPEG ladder: 100 → max_compression_jpg (inclusive) by -2
        self.jpg_qualities = [100] + list(range(98, self.max_compression_jpg - 1, -2))
        if self.jpg_qualities[-1] != self.max_compression_jpg:
            self.jpg_qualities.append(self.max_compression_jpg)

    def optimize(self, media_folder: str):
        logger.info(f"Optimizing media files in: {media_folder}")
        count = 0
        for root, _, files in os.walk(media_folder):
            for name in files:
                full = os.path.join(root, name)
                ext = os.path.splitext(name)[1].lower()

                if ext in (".jpg", ".jpeg"):
                    if not self.optimize_jpg:
                        logger.debug(f"Skip JPG: {full}")
                        continue
                    count += 1
                    self._optimize_jpeg_inplace(full)

                elif ext == ".png":
                    if not self.optimize_png:
                        logger.debug(f"Skip PNG: {full}")
                        continue
                    count += 1
                    self._process_png(full)

        logger.info(f"Media optimization complete. Touched {count} image(s).")

    # -------------------- JPG path (in-place) --------------------

    def _optimize_jpeg_inplace(self, filepath: str):
        try:
            with Image.open(filepath) as im:
                im = ImageOps.exif_transpose(im)
                original = self._read_bytes(filepath)
                best = self._best_jpeg_bytes(im, cap=self.max_size)
                if best and len(best) < len(original):
                    self._write(filepath, best)
                    self._log_gain(filepath, len(original), len(best))
                else:
                    logger.debug(f"No smaller JPG for {os.path.basename(filepath)} ({len(original)//1024} KB)")
        except Exception as e:
            logger.exception(f"Failed to optimize JPG {filepath}: {e}")

    # -------------------- PNG path (convert + resized sibling) --------------------

    def _process_png(self, filepath: str):
        """
        PNG inputs:
        - Keep original PNG untouched.
        - Optionally emit sibling JPEG (optimized, ≤ max_size).
        - Optionally emit sibling resized PNG (no _encode_png used).
        """
        try:
            with Image.open(filepath) as im:
                im = ImageOps.exif_transpose(im)
                base, _ = os.path.splitext(filepath)

                # 1) Converted JPEG sibling (optimized to cap)
                if self.convert_png_to_jpg:
                    jpg_path = f"{base}{self.jpg_suffix}.jpg"
                    jpg_bytes = self._best_jpeg_bytes(im, cap=self.max_size)
                    if jpg_bytes:
                        self._write(jpg_path, jpg_bytes)
                        logger.info(f"Wrote {os.path.basename(jpg_path)} ({len(jpg_bytes)//1024} KB) from PNG source")
                    else:
                        logger.warning(f"Could not produce capped JPEG for {os.path.basename(filepath)}")

                # 2) Resized PNG sibling (bypass _encode_png)
                if self.emit_resized_png:
                    png_path = f"{base}{self.png_suffix}.png"
                    self._emit_resized_png_no_encode(im, png_path)

        except Exception as e:
            logger.exception(f"Failed to process PNG {filepath}: {e}")

    def _emit_resized_png_no_encode(self, img: Image.Image, out_path: str):
        """
        Create a gently downscaled PNG sibling without calling _encode_png.
        Keep key ancillary chunks when present. Try to approach the cap if possible,
        but prioritize being smaller than original; stop at min_side_px.
        """
        # Measure original PNG size if exists; we won't overwrite original.
        original_size = None
        orig_png = os.path.splitext(out_path)[0].replace(self.png_suffix, "") + ".png"
        if os.path.exists(orig_png):
            original_size = os.path.getsize(orig_png)

        # Try iterative downscale (2% default) and save with default PNG writer
        w, h = img.size
        best_bytes: Optional[bytes] = None
        best_len = float("inf")

        current = img.copy()
        while min(w, h) > self.min_side_px:
            # Save attempt with preserved metadata but no custom _encode_png
            attempt = self._save_png_default_bytes(current, img.info)
            if attempt and len(attempt) < best_len:
                best_bytes = attempt
                best_len = len(attempt)

            # Stop if under cap (nice-to-have) or already smaller than original
            if (best_len <= self.max_size) or (original_size and best_len < original_size):
                break

            # gentle 2% shrink (configurable by scale_step)
            w = max(self.min_side_px, ceil(w * (1 - self.scale_step)))
            h = max(self.min_side_px, ceil(h * (1 - self.scale_step)))
            current = current.resize((w, h), Image.LANCZOS)

        if best_bytes:
            self._write(out_path, best_bytes)
            logger.info(f"Wrote {os.path.basename(out_path)} ({best_len//1024} KB)")
        else:
            # fallback: write one pass without resize
            bytes_once = self._save_png_default_bytes(img, img.info)
            if bytes_once:
                self._write(out_path, bytes_once)
                logger.info(f"Wrote {os.path.basename(out_path)} ({len(bytes_once)//1024} KB) (no resize improvement)")

    def _save_png_default_bytes(self, img: Image.Image, info: dict) -> Optional[bytes]:
        """
        Save PNG to bytes WITHOUT using _encode_png. Preserve common metadata.
        """
        buf = io.BytesIO()
        save_kwargs = dict(format="PNG")  # no optimize/compress_level dance
        # Preserve common chunks that affect appearance
        if "icc_profile" in info:
            save_kwargs["icc_profile"] = info.get("icc_profile")
        if "gamma" in info:
            save_kwargs["gamma"] = info.get("gamma")
        if "dpi" in info:
            save_kwargs["dpi"] = info.get("dpi")
        if "transparency" in info:
            save_kwargs["transparency"] = info.get("transparency")
        try:
            img.save(buf, **save_kwargs)
            return buf.getvalue()
        except Exception as e:
            logger.warning(f"Default PNG save failed: {e}")
            return None

    # -------------------- shared helpers --------------------

    def _best_jpeg_bytes(self, img: Image.Image, cap: int) -> Optional[bytes]:
        """
        Try gentle qualities (100→min) and, if needed, gentle 2% downscales to meet cap.
        """
        img_enc = img.convert("RGB")
        attempts = []

        # First: compression without resize
        for q in self.jpg_qualities:
            b = self._encode_jpeg(img_enc, q)
            attempts.append(b)
            if len(b) <= cap:
                break

        best = min(attempts, key=len) if attempts else None
        if best and len(best) <= cap:
            return best

        # Then: gentle downscale loop
        w, h = img_enc.size
        current = img_enc
        best_len = len(best) if best else float("inf")
        while min(w, h) > self.min_side_px:
            w = max(self.min_side_px, ceil(w * (1 - self.scale_step)))
            h = max(self.min_side_px, ceil(h * (1 - self.scale_step)))
            current = current.resize((w, h), Image.LANCZOS)
            for q in self.jpg_qualities:
                b = self._encode_jpeg(current, q)
                if len(b) < best_len:
                    best = b
                    best_len = len(b)
                if best_len <= cap:
                    return best
        return best

    def _encode_jpeg(self, img: Image.Image, quality: int) -> bytes:
        buf = io.BytesIO()
        img.save(
            buf,
            format="JPEG",
            quality=int(quality),
            optimize=True,
            progressive=True,
            subsampling="4:2:0",
        )
        return buf.getvalue()

    @staticmethod
    def _read_bytes(path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    @staticmethod
    def _write(path: str, data: bytes):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    @staticmethod
    def _log_gain(path: str, before: int, after: int):
        pct = 100 * (1 - after / before)
        logger.info(f"Optimized {os.path.basename(path)}: {before//1024} KB → {after//1024} KB ({pct:.1f}% smaller)")

