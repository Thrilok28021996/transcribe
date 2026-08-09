"""Concrete plugin implementations and mock adapters."""

from neural_agent_os.infrastructure.plugins.mock_plugins import (
    MockAlignmentEngine,
    MockDiarizationEngine,
    MockEmbeddingProvider,
    MockKnowledgeExtractor,
    MockLLMProvider,
    MockMarkdownExporter,
    MockSpeakerIdentifier,
    MockSpeechRecognizer,
)

__all__ = [
    "MockAlignmentEngine",
    "MockDiarizationEngine",
    "MockEmbeddingProvider",
    "MockKnowledgeExtractor",
    "MockLLMProvider",
    "MockMarkdownExporter",
    "MockSpeakerIdentifier",
    "MockSpeechRecognizer",
]
