from devworkwire.core.domain.exceptions import (
    DomainException,
    EntityNotFoundException,
    InvalidStatusTransitionException,
    DuplicateEntityException,
    BusinessRuleViolationException,
)


class TestDomainException:
    def test_base_exception_message(self):
        exc = DomainException("Something went wrong")
        assert exc.message == "Something went wrong"
        assert str(exc) == "Something went wrong"


class TestEntityNotFoundException:
    def test_creates_with_entity_type_and_identifier(self):
        exc = EntityNotFoundException("Epic", "PROJ-123")
        assert exc.entity_type == "Epic"
        assert exc.identifier == "PROJ-123"
        assert "Epic not found: PROJ-123" in str(exc)

    def test_is_domain_exception(self):
        exc = EntityNotFoundException("Epic", "PROJ-1")
        assert isinstance(exc, DomainException)


class TestInvalidStatusTransitionException:
    def test_creates_with_valid_transitions(self):
        exc = InvalidStatusTransitionException(
            entity_key="PROJ-1",
            current_status="To Do",
            target_status="Done",
            valid_transitions=["In Progress"],
        )
        assert exc.entity_key == "PROJ-1"
        assert "In Progress" in str(exc)

    def test_creates_without_valid_transitions(self):
        exc = InvalidStatusTransitionException(
            entity_key="PROJ-1",
            current_status="To Do",
            target_status="Done",
        )
        assert "To Do" in str(exc)
        assert "Done" in str(exc)

    def test_is_domain_exception(self):
        exc = InvalidStatusTransitionException("PROJ-1", "A", "B")
        assert isinstance(exc, DomainException)


class TestDuplicateEntityException:
    def test_creates_with_type_and_identifier(self):
        exc = DuplicateEntityException("UserStory", "PROJ-124")
        assert exc.entity_type == "UserStory"
        assert exc.identifier == "PROJ-124"
        assert "Duplicate" in str(exc)

    def test_is_domain_exception(self):
        exc = DuplicateEntityException("Epic", "PROJ-1")
        assert isinstance(exc, DomainException)


class TestBusinessRuleViolationException:
    def test_creates_with_rule_only(self):
        exc = BusinessRuleViolationException("Must have assignee")
        assert exc.rule == "Must have assignee"
        assert exc.entity_key is None
        assert exc.details is None

    def test_creates_with_entity_key(self):
        exc = BusinessRuleViolationException("Must have assignee", entity_key="PROJ-1")
        assert exc.entity_key == "PROJ-1"
        assert "PROJ-1" in str(exc)

    def test_creates_with_all_fields(self):
        exc = BusinessRuleViolationException(
            "Invalid state",
            entity_key="PROJ-1",
            details="Cannot transition from Done to To Do",
        )
        assert "Invalid state" in str(exc)
        assert "PROJ-1" in str(exc)
        assert "Cannot transition" in str(exc)

    def test_is_domain_exception(self):
        exc = BusinessRuleViolationException("Rule broken")
        assert isinstance(exc, DomainException)
