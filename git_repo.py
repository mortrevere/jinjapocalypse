import shutil
import subprocess
import tempfile
from pathlib import Path

from loguru import logger


class GitRepoSource:
    def __init__(self, repo_url):
        self.repo_url = repo_url

    def _run(self, command, cwd=None):
        logger.info("Running: {}", " ".join(command))
        subprocess.run(command, cwd=cwd, check=True)

    def _clone_sparse(self, destination):
        self._run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--filter=blob:none",
                "--sparse",
                self.repo_url,
                str(destination),
            ]
        )
        self._run(["git", "-C", str(destination), "sparse-checkout", "set", "src", "media"])

    def copy_source_tree(self, destination_root="."):
        with tempfile.TemporaryDirectory(prefix="jinjapocalypse-git-") as temp_dir:
            checkout_dir = Path(temp_dir) / "repo"
            self._clone_sparse(checkout_dir)

            destination_root = Path(destination_root)
            for folder_name in ("src", "media"):
                source_path = checkout_dir / folder_name
                if not source_path.exists():
                    raise RuntimeError(f"{folder_name}/ was not found in {self.repo_url}")

                destination_path = destination_root / folder_name
                if destination_path.exists():
                    shutil.rmtree(destination_path)
                shutil.copytree(source_path, destination_path)
                logger.info("Copied {} to {}", source_path, destination_path)
