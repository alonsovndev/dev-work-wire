# CLI Reference

DevWorkWire provides a keyboard-navigable interactive menu, plus direct commands for scripting.

## Launching the CLI

```bash
# Installed from PyPI (recommended via pipx)
dwire

# From a source checkout: convenience script
./scripts/run-cli

# Or directly as a module
python -m devworkwire.presentation.cli
```

Running `dwire` with no arguments prints the startup banner (logo, tagline, and a
"Developed by alonsovndev · v{version}" legend) and starts the interactive menu.
Running `dwire <command> ...` invokes that command directly and exits — no banner or
menu shown.

## Interactive Menu

Navigate with the arrow keys, press Enter to select.

| Option | Description |
|---|---|
| **Retrieve an epic from Jira by key** | Prompts for a Jira issue key, fetches the epic, and prints its title and description |
| **Create a new epic in Jira from a markdown file** | Prompts for a path to an epic Markdown file (see [Markdown Format](markdown-format.md)), parses it, and creates the issue |
| **Exit** | Returns to the shell |

After each action the menu is shown again; select **Exit** to leave.

## Direct Commands

### `dwire fetch-epic KEY`

Fetches an epic from Jira by key and prints its title and description.

```bash
dwire fetch-epic PROJ-123
```

### `dwire create-epic PATH`

Parses a Markdown file (see [Markdown Format](markdown-format.md)) and creates the epic in Jira.

```bash
dwire create-epic path/to/epic.md
```

## Error Handling

Both commands catch errors and print `Error fetching epic: ...` / `Error creating epic: ...` to stderr rather than raising a traceback; the process exits `0` either way (this is a scripting convenience, not a signal to rely on for exit-code checks).

| Error | Cause | Solution |
|---|---|---|
| `ModuleNotFoundError` | Virtual environment not activated | Run `source .venv/bin/activate` |
| Project config error | `devworkwire.yml` missing or invalid | Copy `devworkwire.example.yml` to `devworkwire.yml` and adjust `provider`/`project_key` |
| `Error fetching epic: ...` (404-shaped message) | Epic not found | Verify the Jira key exists |
| `Error fetching/creating epic: ...` (HTTP error) | Jira unreachable or credentials rejected | Check `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` in `.env` |
| `Markdown file not found: ...` | Bad path passed to `create-epic` | Check the file path |

## Roadmap

An import/preview/commit workflow with local state tracking (dedupe by content hash) existed in a prior iteration of this project and was reset during the current baseline reconstruction; it isn't available yet. `features/import_`, `features/progress`, and `features/workitem` are reserved packages for that and related work — see [Architecture Overview](../architecture/overview.md#planned-work).
