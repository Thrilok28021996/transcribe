"""Dependency injection container managing application lifecycles and plugin wiring."""

from __future__ import annotations

from transcribe.application.registry import PluginRegistry
from transcribe.domain.interfaces import (
    AlignmentEngine,
    DiarizationEngine,
    EmbeddingProvider,
    KnowledgeExtractor,
    LLMProvider,
    MarkdownExporter,
    SpeakerIdentifier,
    SpeechRecognizer,
)
from transcribe.infrastructure.config import AppConfig, load_config
from transcribe.infrastructure.plugins.faster_whisper_plugin import (
    FasterWhisperSpeechRecognizer,
)
from transcribe.infrastructure.plugins.mock_plugins import (
    MockAlignmentEngine,
    MockDiarizationEngine,
    MockEmbeddingProvider,
    MockKnowledgeExtractor,
    MockLLMProvider,
    MockMarkdownExporter,
    MockSpeakerIdentifier,
    MockSpeechRecognizer,
)


from transcribe.infrastructure.plugins.llm_extractor import (
    LLMKnowledgeExtractor,
)
from transcribe.infrastructure.plugins.lm_studio_plugin import (
    LMStudioLLMProvider,
)
from transcribe.infrastructure.plugins.markdown_exporter import (
    StandardMarkdownExporter,
)
from transcribe.infrastructure.plugins.speaker_id_plugin import (
    PersistentSpeakerIdentifier,
)
from transcribe.infrastructure.speaker_store import SpeakerDatabase


class ServiceContainer:
    """Central container managing application configuration, registries, and DI wiring."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or load_config()

        # Infrastructure stores
        self.speaker_db = SpeakerDatabase(storage_dir=self.config.storage.speakers_dir)

        # Registries for each AI component interface
        self.speech_recognizers = PluginRegistry[SpeechRecognizer]("SpeechRecognizer")
        self.alignment_engines = PluginRegistry[AlignmentEngine]("AlignmentEngine")
        self.diarization_engines = PluginRegistry[DiarizationEngine]("DiarizationEngine")
        self.speaker_identifiers = PluginRegistry[SpeakerIdentifier]("SpeakerIdentifier")
        self.knowledge_extractors = PluginRegistry[KnowledgeExtractor]("KnowledgeExtractor")
        self.markdown_exporters = PluginRegistry[MarkdownExporter]("MarkdownExporter")
        self.embedding_providers = PluginRegistry[EmbeddingProvider]("EmbeddingProvider")
        self.llm_providers = PluginRegistry[LLMProvider]("LLMProvider")

        # Register default plugins
        self._register_default_plugins()

    def _register_default_plugins(self) -> None:
        """Register built-in mock adapters and real AI model plugins."""
        mock_speech = MockSpeechRecognizer()
        self.speech_recognizers.register("mock", mock_speech)
        self.speech_recognizers.register(mock_speech.name, mock_speech)

        faster_whisper = FasterWhisperSpeechRecognizer(
            model_size=self.config.speech.model_size,
            device=self.config.speech.device,
            compute_type=self.config.speech.compute_type,
            language=self.config.speech.language,
            download_root=self.config.speech.download_root,
        )
        self.speech_recognizers.register("faster-whisper", faster_whisper)

        mock_align = MockAlignmentEngine()
        self.alignment_engines.register("mock", mock_align)
        self.alignment_engines.register(mock_align.name, mock_align)

        mock_diarize = MockDiarizationEngine()
        self.diarization_engines.register("mock", mock_diarize)
        self.diarization_engines.register(mock_diarize.name, mock_diarize)

        persistent_speaker_id = PersistentSpeakerIdentifier(speaker_db=self.speaker_db)
        self.speaker_identifiers.register("mock", persistent_speaker_id)
        self.speaker_identifiers.register("persistent", persistent_speaker_id)

        # LLM Provider (LM Studio local server at http://localhost:1234/v1)
        lm_studio = LMStudioLLMProvider(
            api_base=self.config.llm.api_base,
            model_name=self.config.llm.model_name,
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens,
        )
        self.llm_providers.register("lm-studio", lm_studio)

        mock_llm = MockLLMProvider()
        self.llm_providers.register("mock", mock_llm)

        # Extractor and Exporter
        active_llm = lm_studio if self.config.llm.provider == "lm-studio" else mock_llm
        llm_extractor = LLMKnowledgeExtractor(llm_provider=active_llm)
        self.knowledge_extractors.register("llm-extractor", llm_extractor)
        self.knowledge_extractors.register("lm-studio", llm_extractor)

        mock_extractor = MockKnowledgeExtractor()
        self.knowledge_extractors.register("mock", mock_extractor)

        standard_exporter = StandardMarkdownExporter()
        self.markdown_exporters.register("mock", standard_exporter)
        self.markdown_exporters.register("standard", standard_exporter)

        from transcribe.infrastructure.plugins.lm_studio_embedding import (
            LMStudioEmbeddingProvider,
        )
        lm_embed = LMStudioEmbeddingProvider(api_base=self.config.llm.api_base)
        self.embedding_providers.register("lm-studio", lm_embed)
        self.embedding_providers.register("lm-studio-embeddings", lm_embed)

        mock_embed = MockEmbeddingProvider()
        self.embedding_providers.register("mock", mock_embed)

    # Active component resolvers based on AppConfig
    def get_speech_recognizer(self) -> SpeechRecognizer:
        return self.speech_recognizers.get(self.config.speech.provider)

    def get_alignment_engine(self) -> AlignmentEngine:
        return self.alignment_engines.get("mock")

    def get_diarization_engine(self) -> DiarizationEngine:
        return self.diarization_engines.get(self.config.diarization.provider)

    def get_speaker_identifier(self) -> SpeakerIdentifier:
        return self.speaker_identifiers.get("mock")

    def get_knowledge_extractor(self) -> KnowledgeExtractor:
        return self.knowledge_extractors.get(self.config.llm.provider)

    def get_markdown_exporter(self) -> MarkdownExporter:
        return self.markdown_exporters.get("mock")

    def get_embedding_provider(self) -> EmbeddingProvider:
        return self.embedding_providers.get(self.config.vector_store.provider)

    def get_llm_provider(self) -> LLMProvider:
        return self.llm_providers.get(self.config.llm.provider)
