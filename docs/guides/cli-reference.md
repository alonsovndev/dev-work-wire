# CLI Reference

DevWorkWire provides an interactive menu-driven CLI with InquirerPy, plus direct invocation options for scripting.

## Launching the CLI

```bash
# Installed from PyPI (recommended via pipx)
dwire

# From a source checkout: convenience script
./scripts/run-cli

# Or directly as a module
python -m devworkwire.presentation.cli
```

On launch, you'll see the DevWorkWire welcome screen followed by the main menu.

## Interactive Menu

Navigate with arrow keys and press Enter to select.

### Main Menu Options

| Option                                           | Description                                        |
| ------------------------------------------------ | -------------------------------------------------- |
| **Retrieve an epic and its stories by JIRA key** | Fetches an epic from Jira and displays its details |
| **Create a new epic in JIRA from file**          | Parses a Markdown file and creates an epic in Jira |
| **Import an epic from Markdown**                 | Validate → preview → commit workflow               |
| **Exit the application**                         | Closes the CLI                                     |

### Retrieve an Epic

1. Select **"Retrieve an epic and its stories by JIRA key"**
2. Enter the Jira issue key (e.g., `PROJ-123`)
3. The CLI displays: key, summary, and description

```text
Epic Summary:
Key: PROJ-123
Summary: Backend Modular Monolith Setup
Description: Establish foundational project structure...
```

### Create an Epic from Markdown

1. Select **"Create a new epic in JIRA from file"**
2. Enter the path to an epic Markdown file (defaults to `data/EPIC-0-foundational/epic-0.md`)
3. The tool parses the file, reads `Epic Key`, `Epic Title`, and `Epic Description`, then creates the issue
4. Confirmation with key, summary, and description is displayed

```text
Epic Successfully Created!
Key: PROJ-456
Summary: EPIC-1 - My Feature
Description: ...
```

After each operation, press Enter to return to the main menu.

## Import Commands

The `dwire import` subcommand group provides the validate → preview → commit workflow for loading markdown-defined epics into your project tracker.

### Preview

Parse and validate a markdown file, persisting a preview for later commit:

```bash
dwire import preview path/to/epic.md
```

Displays epic key, title, story count, and validation results. The preview is saved to `.devworkwire/import-preview.json`.

### Commit

Execute the import from a persisted preview:

```bash
dwire import commit          # prompts for confirmation
dwire import commit --yes    # skip confirmation
```

Creates the epic and stories via the configured provider. Deduplicates by source hash — re-importing the same file skips already-imported items.

### Status

List all completed imports from local state:

```bash
dwire import status
```

## Error Handling

| Error                            | Cause                             | Solution                                                               |
| -------------------------------- | --------------------------------- | ---------------------------------------------------------------------- |
| `ModuleNotFoundError`            | Virtual environment not activated | Run `source .venv/bin/activate`                                        |
| `FileNotFoundError`              | Config file missing               | Check `APP_ENV` matches an existing YAML config                        |
| `UnauthorizedWorkspaceAccess`    | Project key mismatch              | Verify `jira.project_key` in YAML config                               |
| `BusinessRuleViolationException` | Invalid epic data                 | Check Markdown file format (see [Markdown Format](markdown-format.md)) |
| `EntityNotFoundException`        | Epic not found in Jira            | Verify the Jira key exists                                             |
| HTTP 401                         | Invalid credentials               | Check `JIRA_EMAIL` and `JIRA_API_TOKEN` in `.env`                      |
