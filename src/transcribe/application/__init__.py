"""Application layer managing workflows, dependency injection, and plugin registries."""

from transcribe.application.container import ServiceContainer
from transcribe.application.registry import PluginRegistry

__all__ = ["PluginRegistry", "ServiceContainer"]
