from unittest.mock import AsyncMock, MagicMock

import pytest

from devworkwire.presentation.cli import main


def _prompt(value):
    prompt = MagicMock()
    prompt.execute.return_value = value
    return prompt


def _menu(monkeypatch, choice, answers):
    selected = iter([choice, main._EXIT])
    entered = iter(answers)
    monkeypatch.setattr(main, "run_menu", MagicMock(side_effect=lambda *_: next(selected)))
    monkeypatch.setattr(
        main.inquirer, "text", MagicMock(side_effect=lambda **_: _prompt(next(entered)))
    )
    monkeypatch.setattr(main.inquirer, "confirm", MagicMock(return_value=_prompt(True)))


def test_exit_choice_stops_the_menu_without_calling_any_action(monkeypatch):
    monkeypatch.setattr(main, "run_menu", MagicMock(return_value=main._EXIT))
    fetch = AsyncMock()
    monkeypatch.setattr(main, "_fetch_epic", fetch)

    main._run_interactive_menu()

    fetch.assert_not_called()


@pytest.mark.parametrize("choice,target", [
    (main._FETCH_EPIC, "_fetch_epic"),
    (main._FETCH_STORY, "_fetch_story"),
    (main._LIST_STORIES, "_list_stories"),
    (main._IMPORT_FOLDER, "_import_folder"),
])
def test_key_and_folder_menu_actions(monkeypatch, choice, target):
    _menu(monkeypatch, choice, ["PROJ-1"])
    action = AsyncMock()
    monkeypatch.setattr(main, target, action)

    main._run_interactive_menu()

    action.assert_awaited_once_with("PROJ-1")


def test_preview_folder_menu_uses_read_only_action(monkeypatch):
    _menu(monkeypatch, main._PREVIEW_FOLDER, ["work-items"])
    preview = MagicMock()
    monkeypatch.setattr(main, "_preview_folder", preview)

    main._run_interactive_menu()

    preview.assert_called_once_with("work-items")


@pytest.mark.parametrize("entered,expected", [
    ("", None),
    ("   ", None),
    ("557058:abcd-1234", "557058:abcd-1234"),
    (" 557058:abcd-1234 ", "557058:abcd-1234"),
])
def test_list_assigned_menu_uses_current_or_explicit_user(monkeypatch, entered, expected):
    _menu(monkeypatch, main._LIST_ASSIGNED, [entered])
    action = AsyncMock()
    monkeypatch.setattr(main, "_list_assigned", action)

    main._run_interactive_menu()

    action.assert_awaited_once_with(expected)


def test_create_epic_menu_prompts_for_fields(monkeypatch):
    _menu(monkeypatch, main._CREATE_EPIC, ["Authentication", "Login work", "High", "auth, backend"])
    create = AsyncMock()
    monkeypatch.setattr(main, "_create_epic", create)

    main._run_interactive_menu()

    create.assert_awaited_once_with(main.WorkItemInput(
        title="Authentication", description="Login work", priority="High",
        labels=("auth", "backend"),
    ))


def test_create_story_menu_prompts_for_parent_and_points(monkeypatch):
    _menu(monkeypatch, main._CREATE_STORY, ["PROJ-1", "Login", "Description", "High", "auth", "5"])
    create = AsyncMock()
    monkeypatch.setattr(main, "_create_story", create)

    main._run_interactive_menu()

    create.assert_awaited_once_with("PROJ-1", main.WorkItemInput(
        title="Login", description="Description", priority="High",
        labels=("auth",), points=5,
    ))


def test_create_story_menu_rejects_invalid_points(monkeypatch, capsys):
    _menu(monkeypatch, main._CREATE_STORY, ["PROJ-1", "Login", "", "", "", "many"])
    create = AsyncMock()
    monkeypatch.setattr(main, "_create_story", create)

    main._run_interactive_menu()

    create.assert_not_called()
    assert "Invalid input" in capsys.readouterr().err
