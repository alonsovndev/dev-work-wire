# CLI Reference

DevWorkWire provides direct commands for scripts and an interactive menu for one-off work.

## Launching the CLI

```bash
# Installed package

dwire

# Source checkout
./scripts/run-cli

# Python module
python -m devworkwire.presentation.cli
```

Running `dwire` without a command opens the menu. Direct commands run without the menu or banner.

## Interactive Menu

Use the arrow keys and Enter to choose an action. The menu can fetch an epic or story, list an epic's stories or a user's assigned work, create one epic or story, preview a folder, or import it after confirmation. The assigned-work prompt accepts a Jira account ID; leave it blank for the authenticated user. Creation prompts for title, description, priority, and labels; story creation also prompts for an existing epic key and whole-number points. Labels are comma-separated in the menu. The menu returns after each action; choose **Exit** to leave.

## Direct Commands

### Create an epic

```bash
dwire create-epic --title "Authentication" --description "Login and recovery" \
  --priority High --label auth --label backend
```

`--title` is required. Description, priority, and repeatable `--label` are optional. This command creates exactly one epic.

### Create a story

```bash
dwire create-story PROJ-123 --title "Log in" --description "A user can log in" \
  --priority High --label auth --points 5
```

The positional key must identify an existing epic. `--title` is required; other options are optional. `--points` accepts a nonnegative whole number and uses the configured `field_mappings.story_points` Jira field.

### Fetch an epic or story

```bash
dwire fetch-epic PROJ-123
dwire fetch-story PROJ-124
```

The detailed view shows key, title, description, priority, and labels when present. Story output also shows parent epic, status, and points when available. Fetch commands reject an issue of the wrong type.

### List an epic's stories

```bash
dwire list-stories PROJ-123
```

Lists every story under the epic as key, title, and status. An empty epic prints a message and succeeds.

### List work assigned to a user

```bash
dwire list-assigned
dwire list-assigned --assignee 557058:abcd-1234
```

Without `--assignee`, the command uses the authenticated Jira user. With it, supply a Jira account ID, not an email address or display name. The command lists open work in the configured project across all issue types, ordered by most recently updated. Each row shows key, issue type, title, and status. “Open” means the Jira status category is not Done. An empty result prints a message and succeeds.

### Preview and validate a folder

```bash
dwire preview-folder path/to/work-items
```

Reads the folder locally without contacting Jira. Shows the epic and each story with compact details, then reports any validation errors with file and line locations. The command exits nonzero if the folder is invalid.

### Import a folder

```bash
dwire import-folder path/to/work-items
dwire import-folder path/to/work-items --yes  # scripts and other non-interactive runs
```

Reads required `epic.md` and optional `stories.md` from the folder (see [Markdown Format](markdown-format.md)). It previews and validates all local items before creating anything. Invalid folders exit without Jira writes. Interactive runs ask for confirmation; non-interactive runs require `--yes`. A declined prompt creates nothing. After confirmation, the epic is created first, then each story is linked to it. Jira story failures are reported individually and the remaining stories are attempted. This command replaces the former `create-epic FOLDER` form.

## Exit Status and Errors

Commands return `0` on success and a nonzero status for missing items, invalid input, Jira errors, a non-interactive import without `--yes`, or any failed story in a folder import. Declining an interactive import exits successfully without creating items. A partial import can still occur after local validation if Jira rejects an item; check the printed keys before retrying to avoid duplicates. Errors are printed to stderr. Configuration comes from `devworkwire.yml` and the Jira environment settings described in [Configuration](../getting-started/configuration.md).
