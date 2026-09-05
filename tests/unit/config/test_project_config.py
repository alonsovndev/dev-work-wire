import pytest

from devworkwire.config.project_config import (
    DEFAULT_FIELD_MAPPINGS,
    ProjectConfig,
)
from devworkwire.core.domain.exceptions import BusinessRuleViolation


def write_config(tmp_path, content: str):
    config_file = tmp_path / "devworkwire.yml"
    config_file.write_text(content, encoding="utf-8")
    return config_file


class TestProjectConfigLoad:
    def test_loads_valid_config(self, tmp_path):
        config_file = write_config(
            tmp_path,
            "provider: jira\nproject_key: PROJ\n",
        )

        config = ProjectConfig.load(config_file)

        assert config.provider == "jira"
        assert config.project_key == "PROJ"
        assert config.field_mappings == DEFAULT_FIELD_MAPPINGS
        assert config.transition_overrides == {}

    def test_field_mappings_merge_with_defaults(self, tmp_path):
        config_file = write_config(
            tmp_path,
            "provider: jira\n"
            "project_key: PROJ\n"
            "field_mappings:\n"
            "  story_points: customfield_99999\n",
        )

        config = ProjectConfig.load(config_file)

        assert config.field_mappings["story_points"] == "customfield_99999"

    def test_transition_overrides_are_loaded(self, tmp_path):
        config_file = write_config(
            tmp_path,
            "provider: jira\n"
            "project_key: PROJ\n"
            "transition_overrides:\n"
            "  In Review: Peer Review\n",
        )

        config = ProjectConfig.load(config_file)

        assert config.transition_overrides == {"In Review": "Peer Review"}

    def test_missing_file_raises_with_hint(self, tmp_path):
        with pytest.raises(BusinessRuleViolation) as exc_info:
            ProjectConfig.load(tmp_path / "does-not-exist.yml")

        assert "devworkwire.example.yml" in str(exc_info.value)

    def test_missing_provider_raises(self, tmp_path):
        config_file = write_config(tmp_path, "project_key: PROJ\n")

        with pytest.raises(BusinessRuleViolation) as exc_info:
            ProjectConfig.load(config_file)

        assert "'provider' is required" in str(exc_info.value)

    def test_unsupported_provider_raises(self, tmp_path):
        config_file = write_config(tmp_path, "provider: linear\nproject_key: PROJ\n")

        with pytest.raises(BusinessRuleViolation) as exc_info:
            ProjectConfig.load(config_file)

        assert "Unsupported provider: linear" in str(exc_info.value)

    def test_missing_project_key_raises(self, tmp_path):
        config_file = write_config(tmp_path, "provider: jira\n")

        with pytest.raises(BusinessRuleViolation) as exc_info:
            ProjectConfig.load(config_file)

        assert "'project_key' is required" in str(exc_info.value)
