import pytest

from devworkwire.application.ports import WorkItemProvider


class TestWorkItemProviderPort:
    def test_port_cannot_be_instantiated_directly(self):
        """The provider port is an abstraction; only adapters implement it."""
        with pytest.raises(TypeError):
            WorkItemProvider()
