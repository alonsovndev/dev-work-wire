import pytest

from devworkwire.core.domain.value_objects import Label
from devworkwire.core.domain.exceptions import BusinessRuleViolationException


class TestLabelCreation:
    def test_create_with_valid_name(self):
        label = Label(name="backend")
        assert label.name == "backend"

    def test_empty_name_raises(self):
        with pytest.raises(BusinessRuleViolationException):
            Label(name="")

    def test_too_long_name_raises(self):
        with pytest.raises(BusinessRuleViolationException):
            Label(name="x" * 256)

    def test_from_optional_with_none(self):
        label = Label.from_optional(None)
        assert label is None

    def test_from_optional_with_value(self):
        label = Label.from_optional("frontend")
        assert label is not None
        assert label.name == "frontend"


class TestLabelImmutability:
    def test_is_frozen(self):
        label = Label(name="backend")
        with pytest.raises(AttributeError):
            label.name = "frontend"


class TestLabelEquality:
    def test_equal_labels_case_insensitive(self):
        label1 = Label(name="Backend")
        label2 = Label(name="backend")
        assert label1 == label2

    def test_different_labels_not_equal(self):
        label1 = Label(name="backend")
        label2 = Label(name="frontend")
        assert label1 != label2

    def test_not_equal_to_non_label(self):
        label = Label(name="backend")
        assert label != "backend"


class TestLabelHashing:
    def test_same_hash_for_case_insensitive(self):
        label1 = Label(name="Backend")
        label2 = Label(name="backend")
        assert hash(label1) == hash(label2)


class TestLabelStringRepresentation:
    def test_str_returns_name(self):
        label = Label(name="backend")
        assert str(label) == "backend"
