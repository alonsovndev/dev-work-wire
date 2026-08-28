import pytest

from devworkwire.core.domain.value_objects import Label, LabelSet
from devworkwire.core.domain.exceptions import BusinessRuleViolationException


class TestLabelSetCreation:
    def test_empty_factory(self):
        ls = LabelSet.empty()
        assert len(ls) == 0

    def test_from_list(self):
        ls = LabelSet.from_list(["backend", "frontend"])
        assert len(ls) == 2

    def test_from_empty_list(self):
        ls = LabelSet.from_list([])
        assert len(ls) == 0

    def test_duplicate_labels_raises(self):
        with pytest.raises(BusinessRuleViolationException):
            LabelSet(labels=(Label("backend"), Label("backend")))


class TestLabelSetImmutability:
    def test_is_frozen(self):
        ls = LabelSet.from_list(["backend"])
        with pytest.raises(AttributeError):
            ls.labels = ()


class TestLabelSetEquality:
    def test_equal_label_sets(self):
        ls1 = LabelSet.from_list(["backend", "frontend"])
        ls2 = LabelSet.from_list(["frontend", "backend"])
        assert ls1 == ls2

    def test_different_label_sets(self):
        ls1 = LabelSet.from_list(["backend"])
        ls2 = LabelSet.from_list(["frontend"])
        assert ls1 != ls2


class TestLabelSetOperations:
    def test_contains(self):
        ls = LabelSet.from_list(["backend"])
        assert ls.contains(Label("backend"))
        assert not ls.contains(Label("frontend"))

    def test_has_label_named_case_insensitive(self):
        ls = LabelSet.from_list(["backend"])
        assert ls.has_label_named("BACKEND")

    def test_add_label(self):
        ls = LabelSet.from_list(["backend"])
        new_ls = ls.add(Label("frontend"))
        assert len(new_ls) == 2
        assert len(ls) == 1  # Original unchanged

    def test_add_duplicate_label(self):
        ls = LabelSet.from_list(["backend"])
        new_ls = ls.add(Label("backend"))
        assert new_ls is ls  # Same instance

    def test_remove_label(self):
        ls = LabelSet.from_list(["backend", "frontend"])
        new_ls = ls.remove(Label("backend"))
        assert len(new_ls) == 1
        assert new_ls.has_label_named("frontend")

    def test_remove_nonexistent_label(self):
        ls = LabelSet.from_list(["backend"])
        new_ls = ls.remove(Label("frontend"))
        assert len(new_ls) == 1


class TestLabelSetIteration:
    def test_iterable(self):
        ls = LabelSet.from_list(["backend", "frontend"])
        names = [label.name for label in ls]
        assert names == ["backend", "frontend"]


class TestLabelSetStringRepresentation:
    def test_str_returns_comma_separated(self):
        ls = LabelSet.from_list(["backend", "frontend"])
        assert str(ls) == "backend, frontend"
