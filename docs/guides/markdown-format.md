# Markdown Format Specification

`dwire create-epic` parses a Markdown file into an `Epic` via `parse_epic_markdown()`
(`features/import_/application/markdown_parser.py`). This is the only Markdown format
currently supported.

## Format

```markdown
# Epic: [Title]
**Description**: [description]
**Priority**: [priority]
**Labels**: [label1, label2]
```

| Field | Required | Description |
|---|---|---|
| `# Epic: [Title]` | No — defaults to `Untitled Epic` | Epic title, on its own heading line |
| `**Description**:` | No — defaults to empty | Free text; may span multiple lines, up to the next `**field**:` or end of file |
| `**Priority**:` | No | Passed through as-is to `Priority.from_jira_name()` |
| `**Labels**:` | No | Comma-separated; each becomes a `Label` (no spaces allowed within a label name) |

### Example

```markdown
# Epic: Backend Modular Monolith Setup

**Description**: Establish foundational project structure, local environment
setup, and CI/CD scaffolding.
**Priority**: High
**Labels**: foundational, backend
```

### How It's Parsed

The parser reads the whole file and extracts each field with a regular expression — order
of fields doesn't matter except that `**Description**:` captures everything up to the next
`**` marker. Missing fields fall back to their defaults; there's no validation beyond what
`Epic.create()` already enforces (a non-empty title after defaulting, valid label
names).

## Roadmap

A richer format supporting linked user stories and acceptance criteria (`stories.md`
alongside `epic.md`) existed in a prior iteration and was reset during the current
baseline reconstruction — see [Architecture Overview](../architecture/overview.md#planned-work).
