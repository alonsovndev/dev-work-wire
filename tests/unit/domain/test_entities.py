import pytest
from devworkwire.core.domain.entities import UserStory, Epic
from devworkwire.core.domain.exceptions import BusinessRuleViolation

def test_create_user_story():
    story = UserStory.create(title="My Story", description="Desc")
    assert story.title == "My Story"

def test_create_user_story_empty_title():
    with pytest.raises(BusinessRuleViolation):
        UserStory.create(title="", description="")

def test_direct_init_user_story_with_valid_data():
    story = UserStory(title="test", description="desc")
    assert story.title == "test"

def test_direct_init_user_story_validates_title():
    with pytest.raises(BusinessRuleViolation):
        UserStory(title="", description="desc")

def test_create_epic():
    epic = Epic.create(title="My Epic", description="Desc")
    assert epic.title == "My Epic"
    epic.add_story(UserStory.create(title="Child", description=""))
    assert len(epic.stories) == 1

def test_create_epic_empty_title():
    with pytest.raises(BusinessRuleViolation):
        Epic.create(title=" ", description="")
