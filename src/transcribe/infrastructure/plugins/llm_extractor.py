"""LLM-backed structured knowledge extractor plugin."""

from __future__ import annotations

import json

from transcribe.domain.entities import (
    Decision,
    ExtractionResult,
    Organization,
    Project,
    Relationship,
    Task,
    Technology,
    Transcript,
)
from transcribe.domain.interfaces import LLMProvider
from transcribe.infrastructure.logging import get_logger

logger = get_logger(__name__)

EXTRACTION_SYSTEM_PROMPT = """You are an expert AI meeting analyst.
Your task is to analyze meeting transcripts and extract structured knowledge into a strictly valid JSON object.

Output format must be JSON with the following schema:
{
  "summary": "High-level 2-3 sentence executive summary of the meeting",
  "decisions": [
    {
      "description": "Clear description of decision made",
      "owner": "Person or team responsible (or null)",
      "confidence": 0.95
    }
  ],
  "tasks": [
    {
      "description": "Clear action item description",
      "owner": "Assignee person (or null)",
      "deadline": "Deadline string if mentioned (or null)",
      "status": "pending",
      "confidence": 0.95
    }
  ],
  "projects": [
    {
      "name": "Project Name",
      "description": "Brief description"
    }
  ],
  "technologies": [
    {
      "name": "Technology Name",
      "category": "Category e.g. Language, Framework, Database"
    }
  ],
  "organizations": [
    {
      "name": "Organization Name"
    }
  ],
  "relationships": [
    {
      "source_id": "Person/Project name",
      "source_type": "Person",
      "target_id": "Task/Technology name",
      "target_type": "Task",
      "relation_type": "owns",
      "confidence": 0.95
    }
  ]
}

Return ONLY raw valid JSON. Do NOT wrap in extra prose or explanations."""


class LLMKnowledgeExtractor:
    """KnowledgeExtractor implementation using an LLMProvider for structured JSON extraction."""

    name: str = "llm-knowledge-extractor"

    def __init__(self, llm_provider: LLMProvider) -> None:
        self.llm_provider = llm_provider

    def _clean_json_text(self, text: str) -> str:
        """Strip markdown triple backticks and trim raw JSON response."""
        cleaned = text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()
        return cleaned

    async def extract(self, transcript: Transcript) -> ExtractionResult:
        """Extract structured entities, decisions, and tasks from transcript text."""
        if not transcript.segments or not transcript.full_text.strip():
            logger.info("Empty transcript detected (no speech segments). Returning empty extraction result.")
            return ExtractionResult(
                meeting_id=transcript.meeting_id,
                summary="No speech detected in audio file.",
                decisions=[],
                tasks=[],
                projects=[],
                technologies=[],
                relationships=[],
            )


        prompt = (
            f"Please analyze the following meeting transcript and extract structured knowledge:\n\n"
            f"--- TRANSCRIPT BEGIN ---\n"
            f"{transcript.full_text}\n"
            f"--- TRANSCRIPT END ---"
        )

        logger.info(f"Extracting knowledge using LLM provider [{self.llm_provider.name}]...")
        raw_response = await self.llm_provider.generate(prompt=prompt, system_prompt=EXTRACTION_SYSTEM_PROMPT)

        json_str = self._clean_json_text(raw_response)
        m_id = transcript.meeting_id

        try:
            data = json.loads(json_str)

            decisions = [
                Decision(
                    meeting_id=m_id,
                    description=d.get("description", ""),
                    owner=d.get("owner"),
                    confidence=float(d.get("confidence", 0.9)),
                )
                for d in data.get("decisions", [])
                if d.get("description")
            ]

            tasks = [
                Task(
                    meeting_id=m_id,
                    description=t.get("description", ""),
                    owner=t.get("owner"),
                    deadline=t.get("deadline"),
                    status=t.get("status", "pending"),
                    confidence=float(t.get("confidence", 0.9)),
                )
                for t in data.get("tasks", [])
                if t.get("description")
            ]

            projects = [
                Project(name=p.get("name", ""), description=p.get("description"))
                for p in data.get("projects", [])
                if p.get("name")
            ]

            technologies = [
                Technology(name=tech.get("name", ""), category=tech.get("category"))
                for tech in data.get("technologies", [])
                if tech.get("name")
            ]

            organizations = [
                Organization(name=org.get("name", ""))
                for org in data.get("organizations", [])
                if org.get("name")
            ]

            relationships = [
                Relationship(
                    source_id=r.get("source_id", ""),
                    source_type=r.get("source_type", "Entity"),
                    target_id=r.get("target_id", ""),
                    target_type=r.get("target_type", "Entity"),
                    relation_type=r.get("relation_type", "related_to"),
                    confidence=float(r.get("confidence", 0.9)),
                )
                for r in data.get("relationships", [])
                if r.get("source_id") and r.get("target_id")
            ]

            return ExtractionResult(
                meeting_id=m_id,
                decisions=decisions,
                tasks=tasks,
                projects=projects,
                technologies=technologies,
                organizations=organizations,
                relationships=relationships,
                summary=data.get("summary", ""),
            )

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as err:
            logger.warning(f"Failed to parse LLM extraction JSON output ({err}). Returning basic extraction.")
            return ExtractionResult(
                meeting_id=m_id,
                summary="Failed to parse LLM output.",
            )
