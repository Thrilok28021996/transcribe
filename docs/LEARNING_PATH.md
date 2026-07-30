# AI Engineering Learning Path

## Purpose

This document is the companion guide for the project.

Its purpose is not merely to explain the code, but to teach the underlying AI concepts, research papers, engineering trade-offs, and production considerations behind every major component.

Every completed milestone should update this document.

---

# Learning Objectives

By the end of this project, you should understand:

- Modern Speech AI
- Speaker Diarization
- Speaker Identification
- Embeddings
- Retrieval-Augmented Generation
- Knowledge Graphs
- Local LLM Deployment
- Agentic Systems
- Evaluation Methodologies
- Production AI System Design

The goal is to become capable of designing similar systems independently.

---

# Module 1 — Audio Fundamentals

## Topics

- Digital audio basics
- Sample rate
- Bit depth
- Mono vs stereo
- PCM
- WAV
- MP3
- AAC
- M4A
- Spectrograms
- Mel spectrograms

## Learn

- Why Whisper uses log-Mel spectrograms
- Why audio preprocessing matters
- Common sources of transcription errors

## Implement

- Audio loader
- Audio normalization
- Resampling pipeline

## Research Papers

- Whisper
- wav2vec 2.0

---

# Module 2 — Speech Recognition

## Learn

How modern ASR works.

Understand:

Traditional

Audio

↓

HMM

↓

GMM

↓

Decoder

Modern

Audio

↓

Transformer

↓

Token probabilities

↓

Beam Search

↓

Transcript

Topics

- Whisper
- CTC
- Beam search
- Greedy decoding
- Language models
- Hallucinations

Implement

- Faster Whisper
- Multiple model support

Research

- Whisper
- wav2vec 2.0
- Conformer

---

# Module 3 — Word Alignment

## Learn

Difference between

Transcription

vs

Forced Alignment

Understand why Whisper timestamps drift.

Topics

- WhisperX
- CTC alignment
- Dynamic Time Warping

Implement

Word-level timestamps.

---

# Module 4 — Speaker Diarization

## Learn

Difference between

Identification

Recognition

Verification

Diarization

Topics

- Speaker embeddings
- Clustering
- Segmentation
- Voice Activity Detection
- Overlapping speech

Metrics

- DER
- JER

Implement

- Diarization engine
- Confidence scoring

Research

- pyannote.audio
- ECAPA-TDNN
- NVIDIA NeMo

---

# Module 5 — Speaker Memory

Learn

How commercial meeting assistants recognize recurring speakers.

Topics

- Speaker embeddings
- Cosine similarity
- Threshold selection
- Incremental learning

Implement

Persistent speaker database.

Research

- SpeakerNet
- ECAPA

---

# Module 6 — Knowledge Extraction

Learn

How LLMs convert conversations into structured knowledge.

Extract

- Decisions
- Tasks
- Risks
- Questions
- Deadlines

Topics

- Prompt engineering
- Structured outputs
- JSON schema validation
- Hallucination detection

Implement

Knowledge extraction pipeline.

---

# Module 7 — Embeddings

Learn

What embeddings represent.

Topics

- Vector spaces
- Similarity search
- Cosine similarity
- Dimensionality
- ANN search

Implement

Embedding abstraction.

Compare

- BGE
- Jina
- Nomic
- E5

---

# Module 8 — Vector Databases

Learn

How ANN indexes work.

Topics

- HNSW
- IVF
- PQ
- DiskANN

Compare

- Qdrant
- Chroma
- LanceDB

Implement

Semantic retrieval.

---

# Module 9 — Knowledge Graphs

Learn

Difference between

Vector Search

vs

Graph Search

Topics

- Nodes
- Edges
- Cypher
- Graph traversal
- Entity resolution

Implement

Knowledge graph generation.

Compare

- Neo4j
- Kuzu
- Memgraph

---

# Module 10 — Retrieval-Augmented Generation

Learn

Complete RAG pipeline.

Document

↓

Chunking

↓

Embedding

↓

Retrieval

↓

Ranking

↓

LLM

↓

Answer

Topics

- Chunking
- Hybrid search
- Re-ranking
- Context windows

Implement

Local RAG.

---

# Module 11 — Agentic Systems

Learn

How autonomous AI systems operate.

Topics

- Planning
- Reflection
- Memory
- Tool use
- MCP
- Function calling
- Multi-agent systems

Implement

Meeting assistant agents.

---

# Module 12 — Evaluation

Every AI system requires objective evaluation.

Speech

- WER
- CER

Diarization

- DER

Retrieval

- Recall@K

LLM

- Faithfulness
- Groundedness

Knowledge Extraction

- Precision
- Recall
- F1

Build an evaluation suite.

---

# Module 13 — Production Engineering

Topics

- Logging
- Monitoring
- Observability
- Benchmarking
- Profiling
- Configuration management
- Plugin systems
- Versioning
- Caching

Implement

Production-quality infrastructure.

---

# Reading List

Speech AI

- Whisper
- wav2vec 2.0
- Conformer

Speaker Recognition

- ECAPA-TDNN
- SpeakerNet

Retrieval

- DPR
- ColBERT
- BGE

Knowledge Graphs

- Neo4j Documentation
- Kuzu Documentation

LLMs

- Attention Is All You Need
- Llama papers
- Qwen technical reports

Agents

- ReAct
- Toolformer
- MRKL
- Voyager

---

# Milestone Checklist

## Phase 1 — Foundation (Completed)

### ✓ What problem did we solve?
Established a clean, extensible, local-first Python software architecture for Transcribe AI. Built immutable domain entities (`Meeting`, `Speaker`, `TranscriptSegment`, `Decision`, `Task`, `Relationship`), type-safe plugin interfaces via Python `Protocol`, a dynamic `PluginRegistry`, a `ServiceContainer` for dependency injection, Pydantic-Settings & YAML configuration management, structured logging, a complete `MeetingService` pipeline orchestrator, mock adapters for early end-to-end execution, and a rich CLI (`transcribe`).

### ✓ Why this design?
- **Domain-Driven Layering**: Keeps business rules and entities strictly decoupled from infrastructure/ML choices (e.g. Faster-Whisper, PyAnnote, Ollama).
- **Python Protocols (Structural Subtyping)**: Allows external or local plugins to be swapped without inheriting from heavy base classes or modifying application code.
- **Pydantic v2 & Pydantic-Settings**: Provides strict schema validation, type safety, environment variable overrides (`TRANSCRIBE_*`), and zero-overhead JSON serialization.
- **Service Container & Plugin Registry**: Enables easy registration, discovery, and dependency injection across all 8 pipeline components.

### ✓ What alternatives were rejected?
- **Heavy DI Frameworks (e.g. dependency-injector)**: Rejected to avoid unnecessary external framework complexity and keep startup times sub-millisecond.
- **Implicit Global Configuration**: Rejected in favor of explicit configuration injection to prevent hidden state bugs and facilitate robust unit testing.
- **Direct Model Coupling**: Hardcoding Whisper or PyAnnote directly in business workflows was rejected to satisfy ADR-002 (Plugin Architecture).

### ✓ Which papers influenced the implementation?
- **Clean Architecture & Domain-Driven Design (Robert C. Martin / Eric Evans)**: Layered boundary enforcement (`Domain` -> `Application` -> `Infrastructure` -> `CLI`).

### ✓ What production issues remain?
- Persistent database storage (SQLite / Qdrant) for long-term meeting indexing will be integrated in Phase 5.
- Speaker diarization (PyAnnote) and speaker memory profile matching will be integrated in Phase 3.

### ✓ What would a commercial system likely do differently?
- A commercial SaaS would use distributed queue workers (Celery, Temporal) for background audio processing instead of single-node async execution.

---

## Phase 2 — Speech Pipeline (Completed)

### ✓ What problem did we solve?
Implemented local speech-to-text transcription and word-level alignment using `faster-whisper` (backed by CTranslate2), audio ingestion (`AudioProcessor`), format validation (`WAV`, `MP3`, `M4A`, `AAC`, `MP4`, `FLAC`, `OGG`), and FFmpeg pre-processing to standard 16kHz mono 16-bit PCM WAV.

### ✓ Why this design?
- **FFmpeg Pre-processing Pipeline**: Converts arbitrary user audio/video containers to 16kHz 16-bit mono WAV before feeding into Whisper, avoiding format decoding errors and optimizing memory usage.
- **Faster-Whisper (CTranslate2)**: Up to 4x faster transcription speed and reduced VRAM/RAM footprint compared to OpenAI's default PyTorch `whisper` library, with native C++ quantization (`int8` / `float16`).
- **Word Timestamps Enabled**: Extracts word-level start/end timestamps directly from cross-attention weights (`word_timestamps=True`) for downstream diarization alignment.

### ✓ What alternatives were rejected?
- **Standard PyTorch `openai-whisper`**: Rejected due to higher memory consumption and slower CPU/GPU inference latency compared to `faster-whisper`.
- **In-memory Audio Resampling in Python**: Rejected in favor of subprocess FFmpeg stream conversion, which scales efficiently to multi-hour audio files without exceeding Python memory limits.

### ✓ Which papers influenced the implementation?
- **Whisper (Radford et al., 2022)**: *Robust Speech Recognition via Large-Scale Weak Supervision*. Encoder-decoder Transformer trained on 680,000 hours of multilingual audio.
- **CTranslate2 Optimization Engine**: Fast inference engine for Transformer models utilizing 8-bit quantization and C++ GEMM backends.

---

## Phase 3 — Speaker Intelligence (Completed)

### ✓ What problem did we solve?
Created a persistent local speaker database (`SpeakerDatabase`), voice embedding matching engine using cosine similarity, incremental centroid vector updates for learning speaker voice profiles over time, temporal reconciler (`reconcile_transcript_with_diarization`), and `PersistentSpeakerIdentifier`.

### ✓ Why this design?
- **Cosine Similarity & Vector Centroids**: Keeps a running average centroid of voice embedding vectors per speaker profile, allowing recognition accuracy to improve across multiple meetings.
- **Temporal Alignment Reconciler**: Reconciles Whisper word timestamps with diarized speaker intervals using maximum time-overlap coverage `max(0, min(word.end, seg.end) - max(word.start, seg.start))`.
- **JSON File Storage**: Simple, human-readable, git-friendly persistence for speaker profiles and embeddings (`speakers.json`).

### ✓ What alternatives were rejected?
- **Hardcoding Speaker Identities per Meeting**: Rejected because meeting memory requires persistent recognition of recurring people across different meetings over time.
- **Static Cosine Thresholds**: Replaced with configurable similarity thresholding (default 0.75) with auto-creation of new speaker profiles when confidence is low.

### ✓ Which papers influenced the implementation?
- **ECAPA-TDNN (Desplanques et al., 2020)**: *Emphasized Channel Attention, Propagation and Aggregation in TDNN Based Speaker Verification*.
- **Speaker Diarization & Verification Survey (Bai & Zhang, 2021)**: Vector embedding distance metrics and online centroid updates.

---

## Phase 4 — Knowledge Extraction (Completed)

### ✓ What problem did we solve?
Integrated open-source LLMs running locally via **LM Studio** (`http://localhost:1234/v1`). Built `LMStudioLLMProvider` with dynamic chat model auto-resolution (`qwen3.5-9b`, `llama-3.2-3b-instruct`), `LLMKnowledgeExtractor` for parsing transcripts into validated `ExtractionResult` entities (Decisions, Action Items, Projects, Technologies, Organizations, Relationships), and `StandardMarkdownExporter` for publishing GFM notes.

### ✓ Why this design?
- **LM Studio OpenAI-Compatible REST API**: Interoperable local HTTP endpoint (`/v1/chat/completions`) providing zero-latency offline LLM inference without external API keys or cloud dependencies.
- **Strict Pydantic JSON Schema Prompting**: Constrains LLM outputs into predictable JSON schemas with automatic clean-up of markdown fences and robust error fallbacks.
- **Dynamic Model Resolution**: Automatically detects active chat models loaded in LM Studio memory (`/v1/models`).

### ✓ What alternatives were rejected?
- **Cloud LLM APIs (OpenAI / Anthropic)**: Rejected to uphold ADR-004 (Offline-first & Privacy-first).
- **Unstructured Free-form LLM Prompts**: Rejected in favor of strict JSON schema extraction to enable automated downstream knowledge graph generation.

### ✓ Which papers influenced the implementation?
- **Function Calling & Structured Outputs with Open Models**: JSON schema constraint enforcement for open LLMs.

---

## Phase 5 — Knowledge Storage (Completed)

### ✓ What problem did we solve?
Implemented persistent local vector indexing (`LocalVectorStore`), local embedding provider (`LMStudioEmbeddingProvider`), Knowledge Graph engine (`KnowledgeGraphStore`), and semantic search & graph explorer service (`SearchService`). Integrated CLI commands `transcribe search` and `transcribe graph`.

### ✓ Why this design?
- **Hybrid Vector + Graph Retrieval**: Vector search retrieves semantically similar transcript chunks and decisions, while the Knowledge Graph traverses entity relationships (`Person --[owns]--> Task`, `Project --[uses]--> Technology`).
- **Nomic-Embed-Text via LM Studio**: Utilizes 768-dimensional local text embeddings (`text-embedding-nomic-embed-text-v1.5`) via `/v1/embeddings` endpoint.
- **Local Persistence**: Vector index (`vectors.json`) and Knowledge Graph (`graph.json`) are stored locally for zero-latency offline access.

### ✓ What alternatives were rejected?
- **Pure Text Keyword Search (BM25)**: Rejected in favor of dense vector embeddings to capture semantic intent and synonyms across meetings.
- **Cloud Vector DBs (Pinecone / Weaviate)**: Rejected to preserve privacy and offline-first capabilities (ADR-004).

### ✓ Which papers influenced the implementation?
- **Dense Passage Retrieval (Karpukhin et al., 2020)**: Semantic passage embedding and cosine similarity retrieval.
- **Graph-Augmented Generation (GraphRAG)**: Combining vector indices with graph relationships for multi-hop reasoning.

---

## Phase 6 — AI Assistant (Completed)

### ✓ What problem did we solve?
Created local Retrieval-Augmented Generation (RAG) assistant service (`RAGAssistantService`) and `transcribe ask "<question>"` CLI tool. Enables answering user questions about past meetings, decisions, action items, technologies, and projects grounded strictly in meeting memory context with source citations.

### ✓ Why this design?
- **Hybrid Context Synthesis**: Combines top-K vector search snippets and Knowledge Graph relationship edges into a single prompt context block.
- **Anti-Hallucination System Prompting**: Instructs local open-source LLMs in LM Studio to answer strictly using retrieved context and admit when information is missing.
- **Source Citations**: Formats and returns retrieved source snippets and relevance scores alongside every LLM answer.

### ✓ What alternatives were rejected?
- **Unbounded Generation Without Context**: Rejected because LLMs hallucinate meeting facts if not constrained by explicit RAG retrieval context.
- **Cloud LLM Q&A API Integration**: Rejected to maintain 100% offline operation and data privacy.

### ✓ Which papers influenced the implementation?
- **RAG (Lewis et al., 2020)**: *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*.
- **Self-RAG / Corrective RAG**: Groundedness verification and context constraint prompting.

---

# Final Outcome

After completing this project, you should be able to:

- Build production AI pipelines.
- Evaluate AI systems rigorously.
- Design modular AI architectures.
- Read and implement research papers.
- Create extensible local-first AI applications.
- Critically assess AI tooling and libraries instead of relying solely on tutorials or defaults.
