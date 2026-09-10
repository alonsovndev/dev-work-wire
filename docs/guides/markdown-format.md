# Markdown Format Specification

`dwire create-epic <folder>` reads `epic.md` (required) and `stories.md` (optional)
from a folder via `parse_epic_markdown()` and `parse_stories_markdown()`
(`features/import_/application/markdown_parser.py`). These are the only Markdown
formats currently supported.

## `epic.md`

```markdown
# Epic: [Title]
**Priority**: [priority]
**Labels**: [label1, label2]

**Epic Description:**
[description, may span multiple paragraphs]

## [Any further heading, e.g. Release Checklist]
[ignored — parsing stops at the next `##` heading or end of file]
```

| Field | Required | Description |
|---|---|---|
| `# Epic: [Title]` | No — defaults to `Untitled Epic` | Epic title, on its own heading line |
| `**Priority**:` | No | Passed through as-is to `Priority.from_jira_name()` |
| `**Labels**:` | No | Comma-separated; each becomes a `Label` (no spaces allowed within a label name) |
| `**Epic Description:**` | No — defaults to empty | Free text; captured up to the next `##` heading or end of file |

Other fields sometimes present in generated epic files (`**Epic Key**`, `**Epic
Title**`, `**Summary**`, `**Components**`, `**Fix Version**`, `**Status**`) are not
modeled by the `Epic` entity today and are ignored.

## `stories.md`

Stories are optional — a missing `stories.md` simply yields no stories. Each story
is a block starting with a `### <Story ID>: <Title>` heading:

```markdown
### US-1: [Title]
**Priority**: [priority]
**Effort Estimate**: [integer story points]
**Labels**: [label1, label2]

**As a** ...,
**I want to** ...,
**So that** ...

**Acceptance Criteria**:

- [ ] ...
- [ ] ...
```

| Field | Required | Description |
|---|---|---|
| `### <id>: [Title]` | Yes (per block) | Story title |
| `**Priority**:` | No | `Priority.from_jira_name()` |
| `**Effort Estimate**:` | No | Integer, becomes `StoryPoints` (parsed for the domain entity only — not sent to Jira; no custom field is configured for it) |
| `**Labels**:` | No | Same rules as the epic's `**Labels**:` |
| `**As a**` / `**I want to**` / `**So that**` + `**Acceptance Criteria**:` | No | Composed into the story's `description` |

Other fields (`**Story ID**`, `**Epic Link**`, `**Issue Type**`, `**Status**`,
`**Fix Version**`, `**Requirements**`, `**Deliverables**`, `**Dependencies**`,
`**Success Metrics**`) are not modeled today and are ignored.

### How It's Parsed

Both parsers read the whole file and extract fields with regular expressions —
field order doesn't matter. Each created Story is linked to its Epic via Jira's
`parent` field, using the issue key returned when the Epic was created. Missing
fields fall back to their defaults; there's no validation beyond what
`Epic.create()`/`UserStory.create()` already enforce (a non-empty title, valid
label names).
