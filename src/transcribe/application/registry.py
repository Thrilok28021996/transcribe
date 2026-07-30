"""Type-safe plugin registry for dynamic AI model registration and selection."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

T = TypeVar("T")


class PluginRegistry(Generic[T]):
    """Registry managing available implementations for a specific plugin interface."""

    def __init__(self, interface_name: str) -> None:
        self.interface_name = interface_name
        self._plugins: dict[str, T] = {}

    def register(self, name: str, plugin_instance: T) -> None:
        """Register a plugin instance under a given name."""
        if name in self._plugins:
            raise ValueError(
                f"Plugin '{name}' already registered in {self.interface_name} registry."
            )
        self._plugins[name] = plugin_instance

    def get(self, name: str) -> T:
        """Retrieve registered plugin instance by name."""
        if name not in self._plugins:
            available = ", ".join(self._plugins.keys()) or "none"
            raise KeyError(
                f"Plugin '{name}' not found in {self.interface_name} registry. Available: [{available}]"
            )
        return self._plugins[name]

    def list_plugins(self) -> list[str]:
        """List names of all registered plugins."""
        return list(self._plugins.keys())

    def clear(self) -> None:
        """Clear all registered plugins."""
        self._plugins.clear()
