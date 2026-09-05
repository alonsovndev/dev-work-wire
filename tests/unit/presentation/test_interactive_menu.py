from unittest.mock import AsyncMock, MagicMock

from devworkwire.presentation.cli import main


def _prompt(value):
    prompt = MagicMock()
    prompt.execute.return_value = value
    return prompt


def test_exit_choice_stops_the_menu_without_calling_any_action(monkeypatch):
    monkeypatch.setattr(main.inquirer, "select", MagicMock(return_value=_prompt(main._EXIT)))
    fetch = AsyncMock()
    create = AsyncMock()
    monkeypatch.setattr(main, "_fetch_epic", fetch)
    monkeypatch.setattr(main, "_create_epic", create)

    main._run_interactive_menu()

    fetch.assert_not_called()
    create.assert_not_called()


def test_retrieve_epic_choice_prompts_for_key_and_fetches(monkeypatch):
    select_values = iter([main._RETRIEVE_EPIC, main._EXIT])
    monkeypatch.setattr(
        main.inquirer, "select", MagicMock(side_effect=lambda **_: _prompt(next(select_values)))
    )
    monkeypatch.setattr(main.inquirer, "text", MagicMock(return_value=_prompt("PROJ-1")))
    monkeypatch.setattr(main.inquirer, "confirm", MagicMock(return_value=_prompt(True)))
    fetch = AsyncMock()
    monkeypatch.setattr(main, "_fetch_epic", fetch)

    main._run_interactive_menu()

    fetch.assert_awaited_once_with("PROJ-1")


def test_create_epic_choice_prompts_for_path_and_creates(monkeypatch):
    select_values = iter([main._CREATE_EPIC, main._EXIT])
    monkeypatch.setattr(
        main.inquirer, "select", MagicMock(side_effect=lambda **_: _prompt(next(select_values)))
    )
    monkeypatch.setattr(main.inquirer, "filepath", MagicMock(return_value=_prompt("epic.md")))
    monkeypatch.setattr(main.inquirer, "confirm", MagicMock(return_value=_prompt(True)))
    create = AsyncMock()
    monkeypatch.setattr(main, "_create_epic", create)

    main._run_interactive_menu()

    create.assert_awaited_once_with("epic.md")
