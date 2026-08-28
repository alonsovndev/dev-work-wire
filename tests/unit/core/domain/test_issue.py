import pytest

from devworkwire.core.domain.exceptions import InvalidStatusTransitionException
from devworkwire.core.domain.issue import IssueStatus


class TestIssueStatus:
    def test_from_jira_status_done(self):
        for status in ["Done", "Closed", "Resolved"]:
            assert IssueStatus.from_jira_status(status) == IssueStatus.DONE

    def test_from_jira_status_in_progress(self):
        for status in ["In Progress", "In Review", "Review"]:
            assert IssueStatus.from_jira_status(status) == IssueStatus.IN_PROGRESS

    def test_from_jira_status_todo(self):
        for status in ["To Do", "Open", "Backlog"]:
            assert IssueStatus.from_jira_status(status) == IssueStatus.TODO

    def test_unknown_status_raises(self):
        with pytest.raises(InvalidStatusTransitionException):
            IssueStatus.from_jira_status("Custom Status")
