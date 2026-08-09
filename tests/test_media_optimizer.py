from pathlib import Path

from PIL import Image

from media_optimizer import MediaOptimizer


def test_estimate_resize_size_respects_cap_and_min_side():
    optimizer = MediaOptimizer(max_size_kb=10, min_side_px=64)

    assert optimizer._estimate_resize_size((1000, 500), current_bytes=100_000, cap=10_000) == (341, 171)
    assert optimizer._estimate_resize_size((64, 64), current_bytes=100_000, cap=10_000) == (64, 64)
    assert optimizer._estimate_resize_size((100, 100), current_bytes=10_000, cap=10_000) == (100, 100)


def test_normalize_jpeg_extension(tmp_path):
    image_path = tmp_path / "photo.jpeg"
    Image.new("RGB", (8, 8), "red").save(image_path)

    normalized = MediaOptimizer()._normalize_jpg_extension(str(image_path))

    assert normalized == str(tmp_path / "photo.jpg")
    assert Path(normalized).exists()
    assert not image_path.exists()


def test_skips_empty_images(tmp_path):
    empty = tmp_path / "empty.jpg"
    empty.write_bytes(b"")

    assert MediaOptimizer()._should_skip_empty_image(str(empty)) is True


def test_process_png_emits_siblings_without_overwriting_original(tmp_path):
    png = tmp_path / "icon.png"
    Image.new("RGBA", (32, 32), (255, 0, 0, 255)).save(png)
    original = png.read_bytes()

    optimizer = MediaOptimizer(
        max_size_kb=20,
        jpg_suffix="-optimized",
        png_suffix="-resized",
    )
    optimizer._process_png(str(png))

    assert png.read_bytes() == original
    assert (tmp_path / "icon-optimized.jpg").exists()
    assert (tmp_path / "icon-resized.png").exists()
