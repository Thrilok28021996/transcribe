# AI Meeting Memory Platform

## Vision

Build a local-first, open-source AI meeting memory platform that transforms conversations into a structured, searchable knowledge base.

Unlike traditional meeting transcription tools, this system should preserve organizational memory by connecting people, projects, decisions, tasks, and knowledge across meetings.

The application should prioritize privacy, extensibility, and offline operation.

---

# Goals

The platform should:

- Record or import meetings
- Produce high-quality transcripts
- Identify speakers
- Learn speaker identities over time
- Extract structured knowledge
- Build a knowledge graph
- Support semantic search
- Enable local AI-powered question answering
- Export portable Markdown

---

# Non-Goals

The first version should NOT attempt:

- Live translation
- Voice cloning
- Video conferencing
- Enterprise user management
- Cloud-only features

---

# Core Features

## 1. Audio Ingestion

Support:

- WAV
- MP3
- AAC
- M4A
- MP4

Future:

- Live microphone recording
- System audio capture

---

## 2. Speech Recognition

Requirements

- Local execution
- Model abstraction
- Batch processing
- GPU optional
- Apple Silicon optimized

Candidate Engines

- faster-whisper
- Parakeet
- whisper.cpp

---

## 3. Word Alignment

Each transcript should contain:

- word
- start time
- end time
- confidence

---

## 4. Speaker Diarization

Generate speaker segments.

Example

Speaker A
00:10–00:35

Speaker B
00:35–00:52

Store confidence for each segment.

---

## 5. Speaker Memory

Maintain persistent speaker profiles.

Each profile should include:

- UUID
- Name
- Aliases
- Voice embeddings
- Confidence history
- Manual corrections
- Meeting history

The system should improve recognition over time.

---

## 6. Knowledge Extraction

Extract:

- Decisions
- Action Items
- Questions
- Risks
- Blockers
- Technologies
- Projects
- Requirements
- Deadlines

Store raw extraction before formatting.

---

## 7. Markdown Knowledge Base

Generate structured Markdown.

Example

meetings/
people/
projects/
topics/

Each meeting should link to related entities.

---

## 8. Vector Search

Enable semantic search across:

- Meetings
- People
- Tasks
- Decisions
- Projects

---

## 9. Knowledge Graph

Represent relationships such as

Person → owns → Task

Project → depends_on → Project

Technology → used_by → Project

Meeting → discusses → Topic

---

## 10. AI Assistant

Support local LLMs.

Capabilities

- Ask questions
- Summarize meetings
- Compare meetings
- Find historical decisions
- Generate follow-up reports

---

# Functional Requirements

- Fully local
- Plugin architecture
- Offline-first
- Modular pipeline
- Cross-platform
- Markdown-first

---

# Quality Goals

Accuracy

Maintain measurable evaluation for:

- transcription
- diarization
- speaker identification
- extraction

Performance

Target processing speed:

- Better than real time on Apple Silicon when feasible.

Reliability

Every stage should recover gracefully from failure.

---

# Extensibility

Every AI component should be replaceable.

Examples

Speech Engine

↓

Whisper

↓

Parakeet

↓

Future Models

without changing downstream code.

---

# Success Criteria

Version 1 should allow a user to:

Import a meeting

↓

Generate transcript

↓

Identify speakers

↓

Extract knowledge

↓

Generate Markdown

↓

Store embeddings

↓

Query meetings using a local LLM

without cloud services.
