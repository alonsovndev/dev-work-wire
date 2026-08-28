import pytest

from devworkwire.core.domain.value_objects import Priority
from devworkwire.core.domain.value_objects.priority import PriorityLevel


class TestPriorityCreation:
    def test_create_from_class_methods(self):
        highest = Priority.highest()
        assert highest.name == "Highest"
        assert highest.level == PriorityLevel.HIGHEST

    def test_from_jira_name_highest(self):
        for name in ["Highest", "Blocker", "Critical"]:
            p = Priority.from_jira_name(name)
            assert p.level == PriorityLevel.HIGHEST

    def test_from_jira_name_high(self):
        for name in ["High", "Major"]:
            p = Priority.from_jira_name(name)
            assert p.level == PriorityLevel.HIGH

    def test_from_jira_name_medium(self):
        for name in ["Medium", "Average", "Normal"]:
            p = Priority.from_jira_name(name)
            assert p.level == PriorityLevel.MEDIUM

    def test_from_jira_name_low(self):
        for name in ["Low", "Minor"]:
            p = Priority.from_jira_name(name)
            assert p.level == PriorityLevel.LOW

    def test_from_jira_name_lowest(self):
        p = Priority.from_jira_name("Lowest")
        assert p.level == PriorityLevel.LOWEST

    def test_from_jira_name_does_not_substring_match(self):
        # Names containing substrings of "lowest" ("west", "owest")
        # must fall back to MEDIUM, not map to LOWEST.
        for name in ["West", "Owest"]:
            p = Priority.from_jira_name(name)
            assert p.level == PriorityLevel.MEDIUM

    def test_from_jira_name_unknown_defaults_to_medium(self):
        p = Priority.from_jira_name("Unknown")
        assert p.level == PriorityLevel.MEDIUM


class TestPriorityImmutability:
    def test_is_frozen(self):
        p = Priority.high()
        with pytest.raises(AttributeError):
            p.name = "Other"


class TestPriorityComparison:
    def test_highest_is_higher_than_high(self):
        assert Priority.highest().is_higher_than(Priority.high())

    def test_high_is_lower_than_highest(self):
        assert Priority.high().is_lower_than(Priority.highest())

    def test_equal_priorities(self):
        p1 = Priority.high()
        p2 = Priority.high()
        assert p1 == p2

    def test_different_priorities_not_equal(self):
        assert Priority.high() != Priority.low()


class TestPriorityStringRepresentation:
    def test_str_returns_name(self):
        p = Priority.high()
        assert str(p) == "High"
