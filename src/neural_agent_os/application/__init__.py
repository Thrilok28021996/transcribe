"""Application layer managing workflows, dependency injection, and plugin registries."""

from neural_agent_os.application.container import ServiceContainer
from neural_agent_os.application.registry import PluginRegistry

__all__ = ["PluginRegistry", "ServiceContainer"]
