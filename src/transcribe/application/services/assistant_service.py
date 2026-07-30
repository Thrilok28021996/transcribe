"""Application service for Retrieval-Augmented Generation (RAG) meeting Q&A assistant."""

from __future__ import annotations

from typing import NamedTuple

from transcribe.application.container import ServiceContainer
from transcribe.application.services.search_service import SearchMatch, SearchService
from transcribe.infrastructure.logging import get_logger

logger = get_logger(__name__)

RAG_SYSTEM_PROMPT = """You are an AI Meeting Memory Assistant.
Your goal is to answer user questions about past meetings, decisions, action items, technologies, and projects.

Strict Rules:
1. Use ONLY the provided context snippets (meeting transcript segments, decisions, tasks, and knowledge graph relationships) to answer the question.
2. If the context does not contain sufficient information to answer the question, state: "Based on the meeting memory, I do not have enough information to answer that question."
3. Do NOT fabricate or assume information outside the provided context.
4. Citing source meeting titles, speaker names, or dates is highly encouraged."""


class RAGAnswer(NamedTuple):
    """Answer object returned by the RAG Assistant."""
    question: str
    answer: str
    sources: list[SearchMatch]
    graph_context: list[str]


class RAGAssistantService:
    """Orchestrates hybrid retrieval and LLM generation for meeting Q&A."""

    def __init__(
        self,
        container: ServiceContainer,
        search_service: SearchService | None = None,
    ) -> None:
        self.container = container
        self.search_service = search_service or SearchService(container=container)

    async def ask(self, question: str, top_k: int = 5) -> RAGAnswer:
        """Answer user question grounded strictly in retrieved meeting memory context."""
        logger.info(f"RAG Assistant processing question: '{question}'")

        # 1. Retrieve hybrid vector matches and graph relationships
        search_result = await self.search_service.search(query=question, top_k=top_k)

        # 2. Build context prompt
        context_parts: list[str] = ["=== RETRIEVED CONTEXT SNIPPETS ==="]
        for idx, match in enumerate(search_result.matches, 1):
            context_parts.append(f"[{idx}] ({match.doc_type.upper()}) {match.text}")

        if search_result.graph_context:
            context_parts.append("\n=== KNOWLEDGE GRAPH RELATIONSHIPS ===")
            for rel in search_result.graph_context:
                context_parts.append(f"• {rel}")

        context_str = "\n".join(context_parts)

        rag_prompt = (
            f"{context_str}\n\n"
            f"=== USER QUESTION ===\n"
            f"{question}\n\n"
            f"Please answer the user question based strictly on the context above."
        )

        # 3. Generate answer using configured LLM Provider (LM Studio)
        llm = self.container.get_llm_provider()
        logger.info(f"Generating grounded answer using LLM provider [{llm.name}]...")
        raw_answer = await llm.generate(prompt=rag_prompt, system_prompt=RAG_SYSTEM_PROMPT)

        return RAGAnswer(
            question=question,
            answer=raw_answer,
            sources=search_result.matches,
            graph_context=search_result.graph_context,
        )
