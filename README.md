# 🤖 Neural Agent OS — Personal Task Automation & Memory Engine

**Neural Agent OS** is a local-first, privacy-focused personal AI operating system and task automation platform. It combines live speech recognition, multi-model routing (Open Source + Cloud AI), progressive autonomy safety ceilings, ambient sidecars, and local vector/graph meeting memory into an intuitive desktop application and CLI tool.

---

## 🌟 Key Features

### 🌐 1. Overview // VYRON OS UX (`vyron-nu.vercel.app` Inspiration)
- **Glassmorphic Neon Aesthetics**: Vibrant dark mode UI with HSL tailored gradients, responsive canvas orb visualizer, and 3D laptop stage mockup.
- **State Visualizer Canvas Orb**: Interactive orb rendering sound frequency waves for `IDLE`, `LISTENING`, `PROCESSING`, `SPEAKING`, and `RECORDING` modes.
- **Developer CLI Terminal**: Built-in runner demonstrating commands (`neural-agent serve`, `neural-agent record`, `neural-agent ask`).

### 🎩 2. Alfred AI Butler Engine (`github.com/ssdavidai/alfred` Inspiration)
- **Progressive Autonomy Tiers (Safety Ceiling)**:
  - ❓ **`Asking`**: Always asks for explicit user instructions (`fail_closed=true`).
  - ⚠️ **`Confirming`**: Presents 1-click confirmation cards for approval (`human_card=true`).
  - ⚡ **`Acting`**: Executes autonomous vault curation and logs to audit ledger (`auto_log=true`).
- **Bring Your Own Model (BYOM)**: Dual-profile router supporting:
  - **Open Source Local Models**: LM Studio, Ollama, vLLM, Faster-Whisper.
  - **Cloud AI Models**: Google Gemini 1.5/2.0, OpenAI GPT-4o, Anthropic Claude 3.5, DeepSeek R1/V3, Groq, OpenRouter.
- **Ambient Sidecars**: Obsidian vault curation, SQLite audit ledger, Vaultwarden secrets manager, Composio/MCP integration mesh.
- **Auditable Audit Ledger**: Real-time signal action console (`#alfredLedgerConsole`).

### 🤖 3. Personal Task Automation Agent
- **Task Automation Hub**: Voice & text custom task execution command bar.
- **Pre-Configured Workflows**:
  - 📊 *Daily Executive Briefing*: Indexes meeting memory & decision logs into markdown summaries.
  - 🧹 *Workspace Storage Sanitizer*: Categorizes raw audio & document storage into format subfolders.
  - 🗑️ *Silent Temp Cache Purge*: Cleans scratch cache and reports freed storage.
  - 🩺 *Hardware & Audio Hook Diagnostics*: Tests audio loopback drivers & model engines.

### 🎙️ 4. Meeting Memory & Local RAG
- **System Audio Loopback**: Captures live Teams, Zoom, or Google Meet calls on macOS via Darwin audio hooks.
- **Real-Time Diarization & Graph Store**: Identifies speakers and constructs local Knowledge Graphs.
- **Local RAG Search**: Perform vector search and grounded Q&A with full source citations.

---

## 🚀 Quick Start

### 1. Installation
```bash
git clone https://github.com/your-username/neural-agent-os.git
cd neural-agent-os
pip install -e .
```

### 2. Launching the Web SPA & Desktop App
- **Native macOS Application**:
  ```bash
  open "dist/Neural Agent OS.app"
  ```
- **FastAPI Web Server**:
  ```bash
  neural-agent serve --port 8000
  ```
  Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 🛠️ CLI Command Reference

| Command | Description | Example |
| :--- | :--- | :--- |
| `neural-agent serve` | Launch the Web Application UX server. | `neural-agent serve --port 8000` |
| `neural-agent record` | Record live audio (`mic`, `system`, or `mixed`). | `neural-agent record -m mixed -d 600 -t "Teams Call"` |
| `neural-agent process <file>` | Process an existing audio file. | `neural-agent process ./call.wav -t "Project Review"` |
| `neural-agent search "<query>"` | Semantic vector search over meeting memory. | `neural-agent search "database architecture"` |
| `neural-agent ask "<question>"` | Ask local RAG assistant questions. | `neural-agent ask "What decisions were made?"` |
| `neural-agent install-cli` | Symlink CLI executable to `~/.local/bin/`. | `neural-agent install-cli` |

---

## 🧪 Testing & Verification
All 60 unit and integration tests can be executed with `pytest`:
```bash
pytest
```
Result: **60 passed in 18s**.
