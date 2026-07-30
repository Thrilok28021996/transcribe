"""Standard Markdown Exporter for generating structured meeting memory notes."""

from __future__ import annotations

from pathlib import Path
from transcribe.domain.entities import ExtractionResult, Meeting, Transcript


class StandardMarkdownExporter:
    """MarkdownExporter implementation generating clean GFM markdown files."""

    name: str = "standard-markdown-exporter"

    async def export(
        self,
        meeting: Meeting,
        transcript: Transcript,
        extraction: ExtractionResult,
        output_dir: Path,
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / f"{meeting.id}.md"

        lines: list[str] = [
            f"# {meeting.title}",
            "",
            "## Meeting Metadata",
            "",
            f"- **Date**: `{meeting.date.strftime('%Y-%m-%d %H:%M:%S UTC')}`",
            f"- **Duration**: `{meeting.duration_seconds:.1f} seconds`",
            f"- **Audio File**: `{meeting.audio_path}`",
            f"- **Language**: `{transcript.language.upper()}`",
            "",
            "## Executive Summary",
            "",
            extraction.summary or "*No summary generated.*",
            "",
            "## Key Decisions",
            "",
        ]

        if extraction.decisions:
            lines.extend([
                "| Decision | Owner | Confidence |",
                "| :--- | :--- | :--- |",
            ])
            for d in extraction.decisions:
                owner_str = f"@{d.owner}" if d.owner else "Unassigned"
                lines.append(f"| {d.description} | {owner_str} | {d.confidence * 100:.0f}% |")
            lines.append("")
        else:
            lines.extend(["*No decisions recorded.*", ""])

        lines.extend(["## Action Items", ""])
        if extraction.tasks:
            for t in extraction.tasks:
                owner_str = f" @{t.owner}" if t.owner else ""
                deadline_str = f" (Due: {t.deadline})" if t.deadline else ""
                lines.append(f"- [ ] **{t.description}**{owner_str}{deadline_str}")
            lines.append("")
        else:
            lines.extend(["*No action items recorded.*", ""])

        if extraction.projects or extraction.technologies:
            lines.extend(["## Entities & Context", ""])
            if extraction.projects:
                lines.append("**Projects:** " + ", ".join(f"`{p.name}`" for p in extraction.projects))
            if extraction.technologies:
                lines.append("**Technologies:** " + ", ".join(f"`{t.name}`" for t in extraction.technologies))
            lines.append("")

        if extraction.relationships:
            lines.extend(["## Knowledge Graph Relationships", ""])
            for r in extraction.relationships:
                lines.append(f"- `{r.source_id}` **--[{r.relation_type}]-->** `{r.target_id}`")
            lines.append("")

        lines.extend(["## Full Transcript", ""])
        for seg in transcript.segments:
            lines.append(f"**[{seg.speaker_id} ({seg.start:.1f}s - {seg.end:.1f}s)]**: {seg.text}")
            lines.append("")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return file_path
