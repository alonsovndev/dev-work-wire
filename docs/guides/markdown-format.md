# Markdown Format Specification

`dwire preview-folder <folder>` and `dwire import-folder <folder>` read `epic.md`
(required) and `stories.md` (optional). Both commands validate the files locally
before any Jira item is created. These are the only Markdown formats supported.

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
| `# Epic: [Title]` | Yes for folder commands | Epic title, on its own heading line |
| `**Priority**:` | No | Passed through as-is to `Priority.from_jira_name()` |
| `**Labels**:` | No | Comma-separated; each becomes a `Label` (no spaces allowed within a label name) |
| `**Epic Description:**` | No — defaults to empty | Free text; captured up to the next `##` heading or end of file |

Other fields sometimes present in generated epic files (`**Epic Key**`, `**Epic
Title**`, `**Summary**`, `**Components**`, `**Fix Version**`, `**Status**`) are not
modeled by the `Epic` entity today and are ignored.

## `stories.md`

Stories are optional — a missing or empty `stories.md` yields no stories. Each story
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
| `**Effort Estimate**:` | No | Nonnegative integer story points, sent to Jira using `field_mappings.story_points` |
| `**Labels**:` | No | Same rules as the epic's `**Labels**:` |
| `**As a**` / `**I want to**` / `**So that**` + `**Acceptance Criteria**:` | No | Composed into the story's `description` |

Other fields (`**Story ID**`, `**Epic Link**`, `**Issue Type**`, `**Status**`,
`**Fix Version**`, `**Requirements**`, `**Deliverables**`, `**Dependencies**`,
`**Success Metrics**`) are not modeled today and are ignored.

### How It's Parsed

Both parsers read the whole file and extract fields with regular expressions;
field order does not matter. Folder validation requires the epic heading and a
title in every story heading. It reports malformed headings, invalid labels,
empty priorities, and estimates that are not nonnegative integers, with file and
line locations. All detectable errors are shown together. Optional fields may
be omitted. Validation is local: Jira can still reject an item because of its
project settings or permissions. Each created Story is linked to its Epic via
Jira's `parent` field, using the key returned when the Epic was created.
