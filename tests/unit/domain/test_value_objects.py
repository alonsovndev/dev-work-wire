import pytest
from devworkwire.core.domain.value_objects import IssueId, Priority, StoryPoints, Label

def test_issue_id_valid():
    issue = IssueId(key="PROJ-123")
    assert issue.key == "PROJ-123"

def test_issue_id_empty():
    with pytest.raises(ValueError):
        IssueId(key="")

def test_priority():
    p = Priority.from_jira_name("High")
    assert p.name == "High"

def test_story_points_valid():
    sp = StoryPoints(value=5)
    assert sp.value == 5

def test_story_points_negative():
    with pytest.raises(ValueError):
        StoryPoints(value=-1)

def test_label_valid():
    lbl = Label(name="frontend")
    assert lbl.name == "frontend"

def test_label_invalid():
    with pytest.raises(ValueError):
        Label(name="")
    with pytest.raises(ValueError):
        Label(name="has space")
