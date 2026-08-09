import os
import subprocess
from pathlib import Path

import pytest

from git_repo import GitRepoSource
from plugin import Notion


def test_notion_requires_api_key(monkeypatch):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="NOTION_API_KEY"):
        Notion().get_block("block-id")


def test_notion_todo_list_extracts_plain_text_and_current_checked_behavior():
    response = {
        "results": [
            {"type": "paragraph"},
            {"type": "to_do", "to_do": {"checked": False, "rich_text": [{"plain_text": "open"}]}},
            {"type": "to_do", "to_do": {"checked": True, "rich_text": [{"plain_text": "done"}]}},
        ]
    }

    notion = Notion()

    assert notion.todo_list(response) == ["open", "done"]
    assert notion.todo_list(response, include_checked=True) == ["open"]


def test_git_repo_source_copies_src_and_optional_media(tmp_path, monkeypatch):
    checkout_root = tmp_path / "checkout"
    repo = checkout_root / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "index.html").write_text("hello", encoding="utf-8")
    destination = tmp_path / "destination"
    destination.mkdir()
    (destination / "src").mkdir()
    (destination / "src" / "old.html").write_text("old", encoding="utf-8")

    def fake_clone_sparse(self, destination_path):
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(repo, destination_path, target_is_directory=True)

    monkeypatch.setattr(GitRepoSource, "_clone_sparse", fake_clone_sparse)

    GitRepoSource("https://example.com/repo.git").copy_source_tree(destination)

    assert (destination / "src" / "index.html").read_text(encoding="utf-8") == "hello"
    assert not (destination / "src" / "old.html").exists()
    assert not (destination / "media").exists()


def write_executable(path, content):
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def test_build_script_runs_docker_without_requiring_uv(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    log = tmp_path / "calls.log"
    repo_root = Path(__file__).resolve().parents[1]

    write_executable(
        fake_bin / "docker",
        f"#!/usr/bin/env sh\nprintf 'docker %s\\n' \"$*\" >> {log}\n",
    )

    subprocess.run(
        [str(repo_root / "build.sh")],
        cwd=tmp_path,
        check=True,
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )

    assert log.read_text(encoding="utf-8").splitlines() == [
        "docker build --build-arg BASE_IMAGE=python:3.12-slim-bookworm -t jinjapocalypse .",
    ]


def test_build_script_propagates_docker_failure(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    log = tmp_path / "calls.log"
    repo_root = Path(__file__).resolve().parents[1]

    write_executable(
        fake_bin / "docker",
        f"#!/usr/bin/env sh\nprintf 'docker %s\\n' \"$*\" >> {log}\nexit 7\n",
    )

    result = subprocess.run(
        [str(repo_root / "build.sh")],
        cwd=tmp_path,
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )

    assert result.returncode == 7
    assert log.read_text(encoding="utf-8").splitlines() == [
        "docker build --build-arg BASE_IMAGE=python:3.12-slim-bookworm -t jinjapocalypse .",
    ]


def test_dockerfile_runs_pytest_in_build_before_runtime_image():
    dockerfile = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM base AS test" in dockerfile
    assert "uv run --locked --no-sync pytest" in dockerfile
    assert "COPY --from=test /app/.tests-passed /tmp/.tests-passed" in dockerfile
    assert "uv sync --locked --no-dev --no-install-project" in dockerfile
