"""Unit tests for LLMKnowledgeExtractor."""

import pytest
from transcribe.domain.entities import Transcript, TranscriptSegment
from transcribe.infrastructure.plugins.llm_extractor import LLMKnowledgeExtractor
from transcribe.infrastructure.plugins.mock_plugins import MockLLMProvider


class CustomLLMProvider:
    name = "custom-mock-llm"

    def __init__(self, json_output: str) -> None:
        self.json_output = json_output

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        return self.json_output


@pytest.mark.asyncio
async def test_llm_knowledge_extractor_success() -> None:
    custom_json = """
    ```json
    {
      "summary": "Team agreed to use Qwen 3.5 via LM Studio.",
      "decisions": [
        {"description": "Adopt Qwen 3.5 for extraction", "owner": "Alice", "confidence": 0.98}
      ],
      "tasks": [
        {"description": "Configure LM Studio endpoint", "owner": "Bob", "deadline": "Today", "status": "pending", "confidence": 0.95}
      ],
      "projects": [{"name": "Transcribe Platform", "description": "Meeting Memory"}],
      "technologies": [{"name": "LM Studio", "category": "LLM Host"}],
      "organizations": [{"name": "AI Team"}],
      "relationships": [
        {"source_id": "Bob", "source_type": "Person", "target_id": "Configure LM Studio endpoint", "target_type": "Task", "relation_type": "owns", "confidence": 0.95}
      ]
    }
    ```
    """
    llm = CustomLLMProvider(json_output=custom_json)
    extractor = LLMKnowledgeExtractor(llm_provider=llm)

    transcript = Transcript(
        meeting_id="test_m1",
        segments=[TranscriptSegment(meeting_id="test_m1", speaker_id="Alice", start=0.0, end=5.0, text="Let's use LM Studio.")],
    )

    result = await extractor.extract(transcript)
    assert result.summary == "Team agreed to use Qwen 3.5 via LM Studio."
    assert len(result.decisions) == 1
    assert result.decisions[0].owner == "Alice"
    assert len(result.tasks) == 1
    assert result.tasks[0].deadline == "Today"
    assert len(result.technologies) == 1
    assert result.technologies[0].name == "LM Studio"
