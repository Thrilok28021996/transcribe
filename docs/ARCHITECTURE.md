# System Architecture

## Philosophy

The system should be modular.

Every AI component must be replaceable without affecting downstream components.

The application should be offline-first and privacy-first.

---

# High-Level Architecture

                Desktop UI
                     │
                     ▼
          Application Services
                     │
      ┌──────────────┴──────────────┐
      │                             │
      ▼                             ▼
 AI Pipeline                 Knowledge Layer
      │                             │
      ▼                             ▼
Infrastructure             Storage Layer

---

# AI Pipeline

Audio

↓

Voice Activity Detection

↓

Speech Recognition

↓

Word Alignment

↓

Speaker Diarization

↓

Speaker Identification

↓

Knowledge Extraction

↓

Markdown Generation

↓

Embedding Pipeline

↓

Knowledge Graph

↓

Local Assistant

---

# Component Boundaries

## UI

Responsibilities

- Import audio
- Display transcripts
- Search
- Chat
- Settings

Never performs AI inference.

---

## Application Layer

Coordinates workflows.

Contains no ML logic.

---

## Domain Layer

Business rules.

Examples

- Meeting
- Speaker
- Task
- Decision
- Project

Independent of frameworks.

---

## Infrastructure

Implements

- Whisper
- Ollama
- Qdrant
- SQLite
- File storage

---

## AI Modules

Speech Recognition

↓

Alignment

↓

Diarization

↓

Knowledge Extraction

↓

Embeddings

↓

RAG

Each module exposes a stable interface.

---

# Design Principles

Dependency inversion.

Plugin architecture.

Configuration-driven.

Strong typing.

Observability.
