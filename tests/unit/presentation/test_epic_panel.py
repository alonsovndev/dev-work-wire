from devworkwire.core.domain.entities import Epic
from devworkwire.core.domain.value_objects import IssueId
from devworkwire.presentation.cli import epic_panel


def _epic(**overrides) -> Epic:
    fields = {
        "title": "Sample Epic",
        "description": "Some description.",
        "issue_id": IssueId(key="PROJ-1"),
    }
    fields.update(overrides)
    return Epic(**fields)


def test_render_epic_panel_contains_key_title_and_description():
    panel = epic_panel.render_epic_panel(_epic())
    assert "Epic: PROJ-1" in panel
    assert "Sample Epic" in panel
    assert "Some description." in panel
    assert panel.startswith("╔")
    assert panel.rstrip().endswith("╝")


def test_render_epic_panel_lines_are_all_the_same_width():
    lines = epic_panel.render_epic_panel(_epic()).splitlines()
    widths = {len(line) for line in lines}
    assert len(widths) == 1


def test_render_epic_panel_wraps_long_description_without_exceeding_width():
    long_description = " ".join(["word"] * 100)
    panel = epic_panel.render_epic_panel(_epic(description=long_description))
    lines = panel.splitlines()
    widths = {len(line) for line in lines}
    assert len(widths) == 1
    assert "word word word" in panel


def test_render_epic_panel_shows_placeholder_for_empty_description():
    panel = epic_panel.render_epic_panel(_epic(description=""))
    assert epic_panel._NO_DESCRIPTION in panel


def test_render_epic_panel_omits_key_line_when_issue_id_missing():
    panel = epic_panel.render_epic_panel(_epic(issue_id=None))
    assert "Epic:" not in panel
