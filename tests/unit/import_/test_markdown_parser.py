from devworkwire.features.import_.application.markdown_parser import (
    parse_epic_markdown,
    parse_stories_markdown,
)

EPIC_MD = """# Epic: User Authentication
**Epic Title**: User Authentication
**Epic Key**: EPIC-2
**Summary**: Implement secure user authentication mechanisms.
**Labels**: authentication, security
**Priority**: Must Have

---

**Epic Description:**
Problem Statement: users need secure account access.

Objective: implement login, logout, and password reset.

## Release Checklist

- [ ] Some release step not part of the description
"""

STORIES_MD = """# Stories for Epic: User Authentication

### US-1: User Authentication Service
**Story ID**: US-1
**Epic Link**: EPIC-2
**Priority**: Must Have
**Effort Estimate**: 8
**Labels**: backend, security

**As a** Backend Engineer,
**I want to** implement a user authentication service,
**So that** users can securely log in.

**Acceptance Criteria**:

- [ ] Given valid credentials, when logging in, then access is granted.
- [ ] Given invalid credentials, when logging in, then access is denied.

**Deliverables**:

- Authentication service.

---

### US-2: Password Reset
**Story ID**: US-2
**Epic Link**: EPIC-2
**Priority**: Should Have

**As a** user,
**I want to** reset my password,
**So that** I can regain access to my account.

**Acceptance Criteria**:

- [ ] Given a reset request, when I provide my email, then a reset link is sent.
"""


def test_parse_epic_markdown_reads_title_priority_labels_and_description(tmp_path):
    epic_file = tmp_path / "epic.md"
    epic_file.write_text(EPIC_MD)

    epic = parse_epic_markdown(str(epic_file))

    assert epic.title == "User Authentication"
    assert epic.priority.name == "Must Have"
    assert [lbl.name for lbl in epic.labels] == ["authentication", "security"]
    assert "Problem Statement: users need secure account access." in epic.description
    assert "Objective: implement login, logout, and password reset." in epic.description
    assert "Release Checklist" not in epic.description


def test_parse_epic_markdown_raises_when_file_missing(tmp_path):
    try:
        parse_epic_markdown(str(tmp_path / "missing.md"))
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_parse_stories_markdown_returns_empty_list_when_file_missing(tmp_path):
    stories = parse_stories_markdown(str(tmp_path / "missing.md"))
    assert stories == []


def test_parse_stories_markdown_parses_each_story_block(tmp_path):
    stories_file = tmp_path / "stories.md"
    stories_file.write_text(STORIES_MD)

    stories = parse_stories_markdown(str(stories_file))

    assert len(stories) == 2

    first, second = stories
    assert first.title == "User Authentication Service"
    assert first.priority.name == "Must Have"
    assert first.story_points.value == 8
    assert [lbl.name for lbl in first.labels] == ["backend", "security"]
    assert "**As a** Backend Engineer" in first.description
    assert "**So that** users can securely log in." in first.description
    assert "Given valid credentials, when logging in, then access is granted." in first.description
    assert "Deliverables" not in first.description

    assert second.title == "Password Reset"
    assert second.priority.name == "Should Have"
    assert second.story_points is None
    assert second.labels == []
