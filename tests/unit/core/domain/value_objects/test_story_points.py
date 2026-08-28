import pytest

from devworkwire.core.domain.value_objects import StoryPoints
from devworkwire.core.domain.exceptions import BusinessRuleViolationException


class TestStoryPointsCreation:
    def test_create_with_positive_value(self):
        sp = StoryPoints(value=5)
        assert sp.value == 5

    def test_create_with_zero(self):
        sp = StoryPoints(value=0)
        assert sp.value == 0

    def test_negative_value_raises(self):
        with pytest.raises(BusinessRuleViolationException):
            StoryPoints(value=-1)

    def test_none_factory(self):
        sp = StoryPoints.none()
        assert sp.value == 0

    def test_from_optional_with_none(self):
        sp = StoryPoints.from_optional(None)
        assert sp is None

    def test_from_optional_with_value(self):
        sp = StoryPoints.from_optional(8)
        assert sp is not None
        assert sp.value == 8


class TestStoryPointsImmutability:
    def test_is_frozen(self):
        sp = StoryPoints(value=5)
        with pytest.raises(AttributeError):
            sp.value = 10


class TestStoryPointsEquality:
    def test_equal_points(self):
        sp1 = StoryPoints(value=5)
        sp2 = StoryPoints(value=5)
        assert sp1 == sp2

    def test_different_points(self):
        sp1 = StoryPoints(value=5)
        sp2 = StoryPoints(value=8)
        assert sp1 != sp2

    def test_not_equal_to_non_story_points(self):
        sp = StoryPoints(value=5)
        assert sp != 5


class TestStoryPointsArithmetic:
    def test_addition(self):
        sp1 = StoryPoints(value=3)
        sp2 = StoryPoints(value=5)
        result = sp1 + sp2
        assert result.value == 8

    def test_multiplication(self):
        sp = StoryPoints(value=3)
        result = sp * 2
        assert result.value == 6

    def test_string_representation(self):
        sp = StoryPoints(value=5)
        assert str(sp) == "5"
