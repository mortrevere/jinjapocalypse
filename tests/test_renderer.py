from pathlib import Path

import pytest

from jinjapocalypse import Jinjapocalypse
from toolbox import Toolbox


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "media").mkdir()
    return tmp_path


def renderer(monkeypatch):
    monkeypatch.setattr("media_optimizer.MediaOptimizer.optimize", lambda self, path: None)
    return Jinjapocalypse()


def test_creates_default_directories(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    renderer(monkeypatch)

    assert (tmp_path / "src").is_dir()
    assert (tmp_path / "media").is_dir()
    assert (tmp_path / "build").is_dir()


def test_renders_hourri_plain_jinja_macros_and_includes(project, monkeypatch):
    (project / "src" / "lib.jinja").write_text(
        "{% macro badge(text) %}<strong>{{ text }}</strong>{% endmacro %}",
        encoding="utf-8",
    )
    (project / "src" / "partial.html").write_text("Partial", encoding="utf-8")
    (project / "src" / "index.html").write_text(
        (
            "/o/ set name = 'Ada' \\o\\\n"
            "Hello \\o/ name \\o/\n"
            "\\o/ src['partial.html'] \\o/\n"
            "{{ badge('Grace') }}\n"
            "{% if True %}plain{% endif %}"
        ),
        encoding="utf-8",
    )

    renderer(monkeypatch).process_files()

    assert (project / "build" / "index.html").read_text(encoding="utf-8") == (
        "Hello Ada\nPartial\n<strong>Grace</strong>\nplain"
    )
    assert (project / "build" / "partial.html").read_text(encoding="utf-8") == "Partial"
    assert not (project / "build" / "lib.jinja").exists()


def test_norender_strips_marker_and_preserves_template_text(project, monkeypatch):
    (project / "src" / "app.html").write_text("!norender\r\n<div>{{ raw }}</div>", encoding="utf-8")

    renderer(monkeypatch).process_files()

    assert (project / "build" / "app.html").read_text(encoding="utf-8") == "<div>{{ raw }}</div>"


def test_empty_rendered_files_are_skipped(project, monkeypatch):
    (project / "src" / "empty.html").write_text("   \n\t", encoding="utf-8")

    renderer(monkeypatch).process_files()

    assert not (project / "build" / "empty.html").exists()


def test_special_sections_create_dynamic_pages(project, monkeypatch):
    (project / "src" / "index.html").write_text(
        "\n".join(
            [
                "before",
                Toolbox.start_page("Fancy Page"),
                "<h1>Dynamic</h1>",
                Toolbox.end_page(),
                "after",
            ]
        ),
        encoding="utf-8",
    )

    renderer(monkeypatch).process_files()

    assert (project / "build" / "fancy-page.html").read_text(encoding="utf-8") == "<h1>Dynamic</h1>"
    assert (project / "build" / "index.html").read_text(encoding="utf-8") == "before\nafter"


def test_unclosed_special_section_raises(project, monkeypatch):
    (project / "src" / "index.html").write_text(
        f"{Toolbox.start_page('Broken')}\nunterminated",
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="Found unclosed section"):
        renderer(monkeypatch).process_files()


def test_copies_media_to_build(project, monkeypatch):
    (project / "src" / "index.html").write_text("ok", encoding="utf-8")
    (project / "media" / "asset.txt").write_text("asset", encoding="utf-8")
    optimized_paths = []

    def record_optimize(self, path):
        optimized_paths.append(Path(path))

    monkeypatch.setattr("media_optimizer.MediaOptimizer.optimize", record_optimize)

    Jinjapocalypse().process_files()

    assert (project / "build" / "media" / "asset.txt").read_text(encoding="utf-8") == "asset"
    assert optimized_paths == [Path("build/media")]
