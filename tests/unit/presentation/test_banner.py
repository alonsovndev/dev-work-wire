from importlib.metadata import PackageNotFoundError

from devworkwire.presentation.cli import banner


def test_render_box_contains_name_and_tagline():
    box = banner.render_box()
    assert "DevWorkWire" in box
    assert banner._TAGLINE in box
    assert box.startswith("╔")
    assert box.rstrip().endswith("╝")


def test_render_box_lines_are_all_the_same_width():
    lines = banner.render_box().splitlines()
    widths = {len(line) for line in lines}
    assert len(widths) == 1


def test_render_legend_contains_author_and_version():
    legend = banner.render_legend()
    assert banner._AUTHOR in legend
    assert banner.app_version() in legend


def test_app_version_falls_back_when_package_not_installed(monkeypatch):
    def _raise(_name):
        raise PackageNotFoundError

    monkeypatch.setattr(banner, "_pkg_version", _raise)

    assert banner.app_version() == "0.0.0-dev"
