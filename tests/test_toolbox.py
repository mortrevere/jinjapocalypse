import json
import re

import pytest

from toolbox import Toolbox


def test_basic_helpers():
    assert Toolbox.hourri() == "\\o/"
    assert Toolbox.slugify(" Café déjà vu! 2026 ") == "café-déjà-vu-2026"
    assert Toolbox.slugify("a b", delimiter="_") == "a_b"
    assert Toolbox.hash("hello", 8) == "2cf24dba"
    assert Toolbox.lookup({"a": 1}, "a") == 1
    assert Toolbox.lookup({}, "missing") == "missing"
    assert Toolbox.lookup({}, "missing", default="fallback") == "fallback"
    assert Toolbox.get_dot_path({"a": {"b": 2}}, "a.b") == 2
    assert Toolbox.get_dot_path({"a": {}}, "a.missing") == {}
    assert sorted(Toolbox.uniq([{"tags": ["b", "a"]}, {"tags": ["a"]}, {}], "tags")) == ["a", "b"]


@pytest.mark.parametrize("path", ["/tmp/x", "src/../secret.txt", "other/file.txt", ".", "src"])
def test_clean_project_path_rejects_unsafe_paths(path):
    with pytest.raises(ValueError):
        Toolbox._clean_project_path(path)


def test_clean_project_path_normalizes_valid_paths():
    assert Toolbox._clean_project_path("src/./posts/page.html") == "src/posts/page.html"
    assert Toolbox._clean_project_path("media\\pics\\one.jpg") == "media/pics/one.jpg"


def test_glob_returns_sorted_filtered_metadata(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "src" / "posts").mkdir(parents=True)
    (tmp_path / "src" / "posts" / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "src" / "posts" / "a.txt").write_text("a", encoding="utf-8")

    files = Toolbox.glob("src/posts/*", kind="file")
    folders = Toolbox.glob("src/*", kind="folder")

    assert [entry["path"] for entry in files] == ["src/posts/a.txt", "src/posts/b.txt"]
    assert files[0] == {
        "path": "src/posts/a.txt",
        "relative_path": "posts/a.txt",
        "root": "src",
        "name": "a.txt",
        "stem": "a",
        "ext": ".txt",
        "kind": "file",
        "is_file": True,
        "is_folder": False,
    }
    assert [entry["path"] for entry in folders] == ["src/posts"]


def test_glob_rejects_unknown_kind(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="kind must be one of"):
        Toolbox.glob("src/*", kind="bad")


def test_read_file_trims_bom_and_returns_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "note.txt").write_text("\ufeff hello \n", encoding="utf-8")
    (tmp_path / "src" / "folder").mkdir()

    assert Toolbox.read_file("src/note.txt") == "hello"
    assert Toolbox.read_file("src/missing.txt", default="fallback") == "fallback"
    with pytest.raises(ValueError, match="Path must point to a file"):
        Toolbox.read_file("src/folder")


def test_load_yaml_reads_from_src(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "data.yaml").write_text("items:\n  - a\n  - b\n", encoding="utf-8")

    assert Toolbox.load_yaml("data.yaml") == {"items": ["a", "b"]}


def test_page_tokens_have_expected_json_payloads():
    def token_payload(token):
        match = re.fullmatch(r"\[---\s+\S+\s+--\s+(\{.*\})\]", token)
        assert match
        return json.loads(match.group(1))

    start_payload = token_payload(Toolbox.start_page("Hello World"))
    end_payload = token_payload(Toolbox.end_page())

    assert start_payload == {"type": "start_page", "page_name": "hello-world"}
    assert end_payload == {"type": "end_page"}
