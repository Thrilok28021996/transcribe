"""Unit tests for type-safe plugin registry."""

import pytest

from neural_agent_os.application.registry import PluginRegistry


class DummyPlugin:
    def __init__(self, name: str) -> None:
        self.name = name


def test_plugin_registry_operations() -> None:
    registry = PluginRegistry[DummyPlugin]("DummyInterface")

    plugin_a = DummyPlugin("alpha")
    registry.register("alpha", plugin_a)

    assert registry.get("alpha") is plugin_a
    assert "alpha" in registry.list_plugins()

    with pytest.raises(ValueError):
        registry.register("alpha", plugin_a)

    with pytest.raises(KeyError):
        registry.get("nonexistent")
