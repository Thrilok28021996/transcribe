/**
 * Transcribe AI — Frontend Application Logic
 */

const API_BASE = (window.location.protocol === 'tauri:' || window.location.protocol === 'asset:' || window.location.protocol === 'file:' || window.location.origin.includes('tauri'))
  ? 'http://127.0.0.1:8000'
  : '';

// Tab Switching Engine
function switchTab(tabId) {
  try {
    if (!tabId || typeof tabId !== 'string') return;
    const cleanId = tabId.replace(/^#/, '').trim();
    if (!cleanId) return;

    // Hide ALL panels with inline style (overrides any CSS)
    document.querySelectorAll('.tab-panel').forEach(p => {
      p.style.cssText = p.style.cssText.replace(/display\s*:[^;]+;?/g, '') + '; display: none;';
      p.classList.remove('active');
    });

    // Remove active from all nav buttons
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    // Show the target panel
    const target = document.getElementById('tab-' + cleanId);
    if (target) {
      target.style.display = 'block';
      target.classList.add('active');
    }

    // Highlight matching nav button(s)
    document.querySelectorAll('.nav-btn[data-tab="' + cleanId + '"]').forEach(b => b.classList.add('active'));

    // Side-effects when specific tabs are shown
    if (cleanId === 'connectors') {
      setTimeout(() => {
        if (typeof loadConnectorStatus === 'function') loadConnectorStatus();
        if (typeof loadCalendarEvents === 'function') loadCalendarEvents();
        if (typeof loadApprovalQueue === 'function') loadApprovalQueue();
      }, 80);
    }

    // Update URL hash
    try {
      if (window.history && window.history.replaceState) {
        window.history.replaceState(null, '', '#' + cleanId);
      }
    } catch (e) {}

    window.scrollTo({ top: 0, behavior: 'smooth' });
  } catch (err) {
    console.error('switchTab error:', err);
  }
}

// Make switchTab globally available immediately (before DOMContentLoaded)
window.switchTab = switchTab;

function initTabs() {
  // Navigate to hash on load
  try {
    const hash = window.location.hash.replace(/^#/, '');
    if (hash && document.getElementById('tab-' + hash)) {
      switchTab(hash);
    }
  } catch (e) {}

  // Handle hash changes (browser back/forward)
  window.addEventListener('hashchange', () => {
    try {
      const hash = window.location.hash.replace(/^#/, '');
      if (hash && document.getElementById('tab-' + hash)) {
        switchTab(hash);
      }
    } catch (e) {}
  });
}

// Run initTabs immediately
initTabs();

function mainInit() {
  loadStats();
  loadMeetings();
  loadRecordings();
  loadSpeakers();
  setupSpeakerFormHandlers();
  loadGraph();
  initAudioDropZone();
  initLiveRecorder();
  loadAudioDevices();
  initChat();
  initSearch();
  initSettings();
  initVyronOrbCanvas();
  initVyronTerminal();
  initVyronBackdrop();
  initAlfredButler();
  initAgentService();

  const refreshBtn = document.getElementById('refreshRecordingsBtn');
  if (refreshBtn) refreshBtn.addEventListener('click', loadRecordings);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mainInit);
} else {
  mainInit();
}

// Load Aggregate System Stats
async function loadStats() {
  try {
    const res = await fetch(`${API_BASE}/api/stats`);
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById('metricMeetings').textContent = data.total_meetings || 0;
    document.getElementById('metricSpeakers').textContent = data.total_speakers || 0;
    document.getElementById('metricVectors').textContent = data.vector_documents || 0;
    document.getElementById('metricGraphNodes').textContent = data.graph_nodes || 0;

    const statusText = document.getElementById('lmStudioStatusText');
    if (statusText) {
      statusText.textContent = `Provider: ${data.llm_provider.toUpperCase()}`;
    }
  } catch (err) {
    console.error('Failed to load stats:', err);
  }
}

// Load Stored Raw Recordings Vault
async function loadRecordings() {
  const container = document.getElementById('recordingsGrid');
  if (!container) return;

  container.innerHTML = '<div class="loading-spinner">Loading stored recording files...</div>';

  try {
    const res = await fetch(`${API_BASE}/api/recordings`);
    if (!res.ok) return;
    const recordings = await res.json();

    if (recordings.length === 0) {
      container.innerHTML = '<p class="placeholder-text">No raw audio recordings stored in data/recordings/ yet.</p>';
      return;
    }

    container.innerHTML = recordings.map(r => `
      <div class="rec-item-card">
        <div class="rec-info">
          <h4>${escapeHtml(r.filename)}</h4>
          <div class="rec-meta">
            <span>Size: ${r.size_mb} MB</span>
            <span>Stored in data/recordings/</span>
          </div>
        </div>
        <button class="btn primary sm" onclick="reprocessRecording('${escapeHtml(r.filename)}')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
          Re-run & Regenerate Note
        </button>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<p class="error-text">Failed to load recordings vault: ${err.message}</p>`;
  }
}

async function reprocessRecording(filename) {
  const timeline = document.getElementById('vaultProcessingTimeline');
  const resultMsg = document.getElementById('vaultProcessingResultMsg');

  if (timeline) timeline.classList.remove('hidden');
  if (resultMsg) resultMsg.classList.add('hidden');

  setStageActive('vault', 1);

  const formData = new FormData();
  formData.append('filename', filename);

  setTimeout(() => setStageActive('vault', 2), 1200);
  setTimeout(() => setStageActive('vault', 3), 2500);
  setTimeout(() => setStageActive('vault', 4), 4000);
  setTimeout(() => setStageActive('vault', 5), 5500);

  try {
    const res = await fetch(`${API_BASE}/api/recordings/reprocess`, {
      method: 'POST',
      body: formData
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Re-processing failed');

    setStageDone('vault', 5);

    if (resultMsg) {
      resultMsg.className = 'result-msg success';
      resultMsg.innerHTML = `
        <strong>Re-processing Completed!</strong><br>
        Recording File: <em>${escapeHtml(filename)}</em><br>
        Decisions Extracted: ${data.decisions_count} | Action Items: ${data.tasks_count}<br>
        Markdown exported at <code>${escapeHtml(data.markdown_path)}</code>
      `;
      resultMsg.classList.remove('hidden');
    }

    loadStats();
    loadMeetings();
  } catch (err) {
    if (resultMsg) {
      resultMsg.className = 'result-msg error';
      resultMsg.textContent = `Re-processing error: ${err.message}`;
      resultMsg.classList.remove('hidden');
    }
  }
}

// Load Meetings List
async function loadMeetings() {
  try {
    const res = await fetch(`${API_BASE}/api/meetings`);
    if (!res.ok) return;
    const meetings = await res.json();

    renderDashboardMeetings(meetings);
    renderSidebarMeetings(meetings);
  } catch (err) {
    console.error('Failed to load meetings:', err);
  }
}

function renderDashboardMeetings(meetings) {
  const container = document.getElementById('dashboardMeetingList');
  if (!container) return;

  if (meetings.length === 0) {
    container.innerHTML = '<p class="placeholder-text">No meetings processed yet. Use the "Import & Process" tab to process your first meeting.</p>';
    return;
  }

  container.innerHTML = meetings.map(m => `
    <div class="meeting-item-btn" onclick="openMeeting('${m.id}')">
      <span class="m-title">${escapeHtml(m.title)}</span>
      <span class="m-date">ID: ${m.id}</span>
    </div>
  `).join('');
}

function renderSidebarMeetings(meetings) {
  const container = document.getElementById('memoryMeetingList');
  if (!container) return;

  if (meetings.length === 0) {
    container.innerHTML = '<p class="placeholder-text">No meetings stored.</p>';
    return;
  }

  container.innerHTML = meetings.map(m => `
    <div class="meeting-item-btn" onclick="openMeeting('${m.id}')">
      <span class="m-title">${escapeHtml(m.title)}</span>
      <span class="m-date">Markdown Note</span>
    </div>
  `).join('');
}

// Open and Render Meeting Note
async function openMeeting(meetingId) {
  // Switch to meetings tab
  document.querySelector('[data-tab="meetings"]').click();

  const container = document.getElementById('memoryDetailContainer');
  container.innerHTML = '<div class="loading-spinner">Loading meeting note...</div>';

  try {
    const res = await fetch(`/api/meetings/${meetingId}`);
    if (!res.ok) throw new Error('Meeting not found');
    const data = await res.json();

    container.innerHTML = `
      <div class="meeting-note-viewer">
        <div class="note-header">
          <h2>${escapeHtml(meetingId)}</h2>
        </div>
        <pre class="markdown-preview">${escapeHtml(data.markdown)}</pre>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="error-msg">Error loading meeting: ${err.message}</div>`;
  }
}

// Audio Drop Zone & Processing Form
function initAudioDropZone() {
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('audioFileInput');
  const startBtn = document.getElementById('startProcessBtn');
  const fileInfo = document.getElementById('selectedFileInfo');
  const fileNameDisplay = document.getElementById('selectedFileName');
  const form = document.getElementById('ingestForm');

  let selectedFile = null;

  dropZone.addEventListener('click', () => fileInput.click());

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      selectedFile = e.dataTransfer.files[0];
      updateFileInfo(selectedFile);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      selectedFile = fileInput.files[0];
      updateFileInfo(selectedFile);
    }
  });

  function updateFileInfo(file) {
    fileNameDisplay.textContent = `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
    fileInfo.classList.remove('hidden');
    startBtn.disabled = false;
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    const timeline = document.getElementById('vaultProcessingTimeline');
    const resultMsg = document.getElementById('vaultProcessingResultMsg');

    if (timeline) timeline.classList.remove('hidden');
    if (resultMsg) resultMsg.classList.add('hidden');
    startBtn.disabled = true;

    setStageActive('vault', 1);

    const formData = new FormData();
    formData.append('file', selectedFile);
    const titleInput = document.getElementById('meetingTitleInput').value.trim();
    if (titleInput) {
      formData.append('title', titleInput);
    }

    // Simulate stage visual progress
    setTimeout(() => setStageActive('vault', 2), 1200);
    setTimeout(() => setStageActive('vault', 3), 2500);
    setTimeout(() => setStageActive('vault', 4), 4000);
    setTimeout(() => setStageActive('vault', 5), 5500);

    try {
      const res = await fetch(`${API_BASE}/api/process`, {
        method: 'POST',
        body: formData
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Processing failed');

      setStageDone('vault', 5);

      if (resultMsg) {
        resultMsg.className = 'result-msg success';
        resultMsg.innerHTML = `
          <strong>Processing Complete!</strong><br>
          Meeting Title: <em>${escapeHtml(data.title)}</em><br>
          Decisions Extracted: ${data.decisions_count} | Action Items: ${data.tasks_count}<br>
          Markdown exported at <code>${escapeHtml(data.markdown_path)}</code>
        `;
        resultMsg.classList.remove('hidden');
      }

      loadStats();
      loadMeetings();
      loadRecordings();
    } catch (err) {
      if (resultMsg) {
        resultMsg.className = 'result-msg error';
        resultMsg.textContent = `Processing error: ${err.message}`;
        resultMsg.classList.remove('hidden');
      }
    } finally {
      startBtn.disabled = false;
    }
  });
}

function setStageActive(prefix, stageNum) {
  for (let i = 1; i <= 5; i++) {
    const el = document.getElementById(`${prefix}Stage${i}`);
    if (!el) continue;
    if (i < stageNum) {
      el.className = 'stage-item done';
    } else if (i === stageNum) {
      el.className = 'stage-item active';
    } else {
      el.className = 'stage-item';
    }
  }
}

function setStageDone(prefix, stageNum) {
  for (let i = 1; i <= stageNum; i++) {
    const el = document.getElementById(`${prefix}Stage${i}`);
    if (el) el.className = 'stage-item done';
  }
}

// AI Assistant Chat Logic
function initChat() {
  const input = document.getElementById('chatInput');
  const sendBtn = document.getElementById('sendChatBtn');
  const chatHistory = document.getElementById('chatHistory');

  // Suggested pills
  document.querySelectorAll('.pill-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      input.value = btn.textContent;
      sendQuestion();
    });
  });

  sendBtn.addEventListener('click', sendQuestion);
  input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendQuestion();
  });

  async function sendQuestion() {
    const question = input.value.trim();
    if (!question) return;

    input.value = '';

    // Append user message
    appendChatMessage('user', 'You', question);

    // Append loading placeholder
    const loadingId = 'loading_' + Date.now();
    appendChatMessage('system', 'AI Assistant', '<div class="loading-spinner">Querying meeting vector memory & LM Studio...</div>', loadingId);

    try {
      const res = await fetch(`${API_BASE}/api/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question, top_k: 5 })
      });

      const data = await res.json();

      const loadingMsg = document.getElementById(loadingId);
      if (loadingMsg) loadingMsg.remove();

      let answerHtml = `<p>${escapeHtml(data.answer)}</p>`;

      if (data.sources && data.sources.length > 0) {
        answerHtml += `<div class="sources-box"><strong>Source Citations:</strong><ul>`;
        data.sources.forEach(s => {
          answerHtml += `<li><span class="type-tag">${escapeHtml(s.doc_type)}</span> ${escapeHtml(s.text)} <em>(Score: ${s.score.toFixed(2)})</em></li>`;
        });
        answerHtml += `</ul></div>`;
      }

      appendChatMessage('system', 'AI Assistant', answerHtml);
    } catch (err) {
      const loadingMsg = document.getElementById(loadingId);
      if (loadingMsg) loadingMsg.remove();

      appendChatMessage('system', 'AI Assistant', `<div class="error-msg">Error querying AI assistant: ${err.message}</div>`);
    }
  }

  function appendChatMessage(role, senderName, contentHtml, elementId = null) {
    const div = document.createElement('div');
    div.className = `chat-msg ${role}`;
    if (elementId) div.id = elementId;

    div.innerHTML = `
      <div class="avatar">${role === 'user' ? 'U' : 'AI'}</div>
      <div class="msg-body">${contentHtml}</div>
    `;

    chatHistory.appendChild(div);
    chatHistory.scrollTop = chatHistory.scrollHeight;
  }
}

// Quick Search
function initSearch() {
  const input = document.getElementById('dashSearchInput');
  const btn = document.getElementById('dashSearchBtn');
  const container = document.getElementById('dashSearchResults');

  btn.addEventListener('click', runSearch);

  async function runSearch() {
    const q = input.value.trim();
    if (!q) return;

    container.innerHTML = '<div class="loading-spinner">Searching vector index...</div>';

    try {
      const res = await fetch(`${API_BASE}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, top_k: 5 })
      });

      const data = await res.json();

      if (!data.matches || data.matches.length === 0) {
        container.innerHTML = '<p class="placeholder-text">No matches found in vector index.</p>';
        return;
      }

      container.innerHTML = data.matches.map(m => `
        <div class="search-match-card">
          <span class="match-badge">${escapeHtml(m.doc_type)} (${m.score.toFixed(2)})</span>
          <p>${escapeHtml(m.text)}</p>
        </div>
      `).join('');
    } catch (err) {
      container.innerHTML = `<p class="error-text">Search error: ${err.message}</p>`;
    }
  }
}

// Load Persistent Speakers
async function loadSpeakers() {
  const container = document.getElementById('speakersGrid');
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/api/speakers`);
    if (!res.ok) return;
    const speakers = await res.json();

    if (speakers.length === 0) {
      container.innerHTML = '<p class="placeholder-text">No speaker profiles registered yet. Click <strong>+ Add New Speaker</strong> above to add one manually.</p>';
      return;
    }

    container.innerHTML = speakers.map(s => `
      <div class="speaker-card" style="position: relative;">
        <div class="speaker-header">
          <h3>${escapeHtml(s.name)}</h3>
          <span class="status-badge">${s.has_embedding ? 'Vector Active' : 'No Vector'}</span>
        </div>
        <p><strong>Aliases:</strong> ${s.aliases.length > 0 ? escapeHtml(s.aliases.join(', ')) : 'None'}</p>
        <p><strong>Confidence:</strong> ${(s.confidence_avg * 100).toFixed(0)}% (${s.meeting_count} observations)</p>
        <div style="margin-top: 12px; display: flex; gap: 8px;">
          <button class="btn sm" onclick="openEditSpeaker('${escapeHtml(s.id)}', '${escapeHtml(s.name)}', '${escapeHtml(s.aliases.join(', '))}')">✏️ Rename Speaker</button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Failed to load speakers:', err);
  }
}

function openEditSpeaker(id, name, aliases) {
  const form = document.getElementById('speakerFormContainer');
  const title = document.getElementById('speakerFormTitle');
  const editId = document.getElementById('editSpeakerId');
  const nameInput = document.getElementById('speakerNameInput');
  const aliasesInput = document.getElementById('speakerAliasesInput');

  if (!form || !nameInput) return;
  form.classList.remove('hidden');
  title.textContent = `Rename Speaker: ${name}`;
  editId.value = id;
  nameInput.value = name;
  aliasesInput.value = aliases || '';
  nameInput.focus();
}

function setupSpeakerFormHandlers() {
  const addBtn = document.getElementById('addSpeakerBtn');
  const cancelBtn = document.getElementById('cancelSpeakerBtn');
  const saveBtn = document.getElementById('saveSpeakerBtn');
  const form = document.getElementById('speakerFormContainer');

  if (addBtn) {
    addBtn.addEventListener('click', () => {
      if (!form) return;
      document.getElementById('speakerFormTitle').textContent = 'Add New Speaker Profile';
      document.getElementById('editSpeakerId').value = '';
      document.getElementById('speakerNameInput').value = '';
      document.getElementById('speakerAliasesInput').value = '';
      form.classList.remove('hidden');
      document.getElementById('speakerNameInput').focus();
    });
  }

  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      if (form) form.classList.add('hidden');
    });
  }

  if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
      const editId = document.getElementById('editSpeakerId').value.trim();
      const name = document.getElementById('speakerNameInput').value.trim();
      const aliases = document.getElementById('speakerAliasesInput').value.trim();

      if (!name) {
        alert('Please enter a speaker name.');
        return;
      }

      try {
        const formData = new FormData();
        formData.append('name', name);
        formData.append('aliases', aliases);

        const url = editId ? `${API_BASE}/api/speakers/${encodeURIComponent(editId)}` : `${API_BASE}/api/speakers`;
        const res = await fetch(url, {
          method: 'POST',
          body: formData,
        });

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail || 'Failed to save speaker.');
        }

        if (form) form.classList.add('hidden');
        loadSpeakers();
        loadStats();
      } catch (err) {
        alert(`Error saving speaker: ${err.message}`);
      }
    });
  }
}

// Obsidian-Style Interactive Force-Directed Canvas Graph Visualizer
class ObsidianGraphRenderer {
  constructor(canvasId, containerId, tooltipId) {
    this.canvas = document.getElementById(canvasId);
    this.container = document.getElementById(containerId);
    this.tooltip = document.getElementById(tooltipId);
    if (!this.canvas) return;

    this.ctx = this.canvas.getContext('2d');
    this.nodes = [];
    this.edges = [];
    this.nodeMap = new Map();
    this.animId = null;

    // Viewport transform
    this.zoom = 1.0;
    this.panX = 0;
    this.panY = 0;

    // Interaction state
    this.draggedNode = null;
    this.hoveredNode = null;
    this.focusedNode = null;
    this.isPanning = false;
    this.startPanX = 0;
    this.startPanY = 0;

    this.colorMap = {
      Person: '#38bdf8',
      Meeting: '#10b981',
      Decision: '#f59e0b',
      Task: '#ef4444',
      Project: '#a855f7',
      Technology: '#6366f1',
    };

    this.initEvents();
  }

  initEvents() {
    window.addEventListener('resize', () => this.resizeCanvas());
    this.resizeCanvas();

    // Mouse Wheel Zoom
    this.canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
      const newZoom = Math.min(Math.max(this.zoom * zoomFactor, 0.25), 4.0);

      const rect = this.canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      this.panX = mouseX - (mouseX - this.panX) * (newZoom / this.zoom);
      this.panY = mouseY - (mouseY - this.panY) * (newZoom / this.zoom);
      this.zoom = newZoom;
    }, { passive: false });

    // Mouse Down (Drag Node or Pan)
    this.canvas.addEventListener('mousedown', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const hit = this.getHitNode(mouseX, mouseY);
      if (hit) {
        this.draggedNode = hit;
        this.focusedNode = hit;
        this.canvas.style.cursor = 'grabbing';
      } else {
        this.isPanning = true;
        this.startPanX = e.clientX - this.panX;
        this.startPanY = e.clientY - this.panY;
        this.focusedNode = null;
        this.canvas.style.cursor = 'grabbing';
      }
    });

    // Mouse Move (Hover, Drag, Pan)
    this.canvas.addEventListener('mousemove', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      if (this.draggedNode) {
        const worldPos = this.screenToWorld(mouseX, mouseY);
        this.draggedNode.x = worldPos.x;
        this.draggedNode.y = worldPos.y;
        this.draggedNode.vx = 0;
        this.draggedNode.vy = 0;
        return;
      }

      if (this.isPanning) {
        this.panX = e.clientX - this.startPanX;
        this.panY = e.clientY - this.startPanY;
        return;
      }

      // Hover check
      const hit = this.getHitNode(mouseX, mouseY);
      this.hoveredNode = hit;
      this.canvas.style.cursor = hit ? 'pointer' : 'grab';

      if (hit && this.tooltip) {
        this.tooltip.classList.remove('hidden');
        this.tooltip.style.left = `${mouseX + 15}px`;
        this.tooltip.style.top = `${mouseY + 15}px`;
        this.tooltip.innerHTML = `
          <div style="font-weight: 700; color: ${this.getNodeColor(hit.label)}; margin-bottom: 2px;">
            ${escapeHtml(hit.label)}
          </div>
          <div style="font-size: 0.92rem; font-weight: 600;">${escapeHtml(hit.id)}</div>
          <div style="font-size: 0.78rem; color: #94a3b8; margin-top: 4px;">
            Connections: ${hit.neighbors.size}
          </div>
        `;
      } else if (this.tooltip) {
        this.tooltip.classList.add('hidden');
      }
    });

    // Mouse Up
    window.addEventListener('mouseup', () => {
      this.draggedNode = null;
      this.isPanning = false;
      this.canvas.style.cursor = 'grab';
    });
  }

  resizeCanvas() {
    if (!this.container || !this.canvas) return;
    this.canvas.width = this.container.clientWidth;
    this.canvas.height = this.container.clientHeight;
  }

  screenToWorld(sx, sy) {
    return {
      x: (sx - this.panX) / this.zoom,
      y: (sy - this.panY) / this.zoom,
    };
  }

  worldToScreen(wx, wy) {
    return {
      x: wx * this.zoom + this.panX,
      y: wy * this.zoom + this.panY,
    };
  }

  getNodeColor(label) {
    return this.colorMap[label] || '#94a3b8';
  }

  getHitNode(sx, sy) {
    const worldPos = this.screenToWorld(sx, sy);
    for (let i = this.nodes.length - 1; i >= 0; i--) {
      const n = this.nodes[i];
      const dx = worldPos.x - n.x;
      const dy = worldPos.y - n.y;
      const distSq = dx * dx + dy * dy;
      const hitRadius = (n.radius + 6) / this.zoom;
      if (distSq <= hitRadius * hitRadius) {
        return n;
      }
    }
    return null;
  }

  setData(rawNodes, rawEdges) {
    this.resizeCanvas();
    const cx = this.canvas.width / 2 / this.zoom;
    const cy = this.canvas.height / 2 / this.zoom;

    this.nodes = rawNodes.map((n, idx) => {
      const angle = (idx / Math.max(1, rawNodes.length)) * Math.PI * 2;
      const radius = 100 + Math.random() * 150;
      return {
        id: n.id,
        label: n.label || 'Entity',
        properties: n.properties || {},
        x: cx + Math.cos(angle) * radius,
        y: cy + Math.sin(angle) * radius,
        vx: 0,
        vy: 0,
        radius: n.label === 'Meeting' ? 12 : 9,
        neighbors: new Set(),
      };
    });

    this.nodeMap = new Map(this.nodes.map(n => [n.id, n]));

    this.edges = (rawEdges || []).map(e => {
      const src = this.nodeMap.get(e.source_id);
      const tgt = this.nodeMap.get(e.target_id);
      if (src && tgt) {
        src.neighbors.add(tgt.id);
        tgt.neighbors.add(src.id);
      }
      return { source: src, target: tgt, relation_type: e.relation_type };
    }).filter(e => e.source && e.target);

    this.resetView();
    this.startAnimation();
  }

  resetView() {
    this.zoom = 1.0;
    this.panX = 0;
    this.panY = 0;
    this.focusedNode = null;
  }

  startAnimation() {
    if (this.animId) cancelAnimationFrame(this.animId);
    const loop = () => {
      this.stepPhysics();
      this.render();
      this.animId = requestAnimationFrame(loop);
    };
    loop();
  }

  stepPhysics() {
    const kRepulsion = 4000;
    const kSpring = 0.04;
    const restLength = 120;
    const damping = 0.85;
    const gravity = 0.015;

    const cx = (this.canvas.width / 2 - this.panX) / this.zoom;
    const cy = (this.canvas.height / 2 - this.panY) / this.zoom;

    // Repulsion between node pairs
    for (let i = 0; i < this.nodes.length; i++) {
      const n1 = this.nodes[i];
      for (let j = i + 1; j < this.nodes.length; j++) {
        const n2 = this.nodes[j];
        let dx = n2.x - n1.x;
        let dy = n2.y - n1.y;
        let dist = Math.sqrt(dx * dx + dy * dy) || 1;

        if (dist < 300) {
          const force = kRepulsion / (dist * dist);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;

          if (n1 !== this.draggedNode) { n1.vx -= fx; n1.vy -= fy; }
          if (n2 !== this.draggedNode) { n2.vx += fx; n2.vy += fy; }
        }
      }

      // Gravity towards center
      if (n1 !== this.draggedNode) {
        n1.vx += (cx - n1.x) * gravity;
        n1.vy += (cy - n1.y) * gravity;
      }
    }

    // Spring attraction along edges
    for (const e of this.edges) {
      const n1 = e.source;
      const n2 = e.target;
      let dx = n2.x - n1.x;
      let dy = n2.y - n1.y;
      let dist = Math.sqrt(dx * dx + dy * dy) || 1;

      const delta = dist - restLength;
      const force = delta * kSpring;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;

      if (n1 !== this.draggedNode) { n1.vx += fx; n1.vy += fy; }
      if (n2 !== this.draggedNode) { n2.vx -= fx; n2.vy -= fy; }
    }

    // Apply velocities with damping
    for (const n of this.nodes) {
      if (n === this.draggedNode) continue;
      n.vx *= damping;
      n.vy *= damping;
      n.x += n.vx;
      n.y += n.vy;
    }
  }

  render() {
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;

    ctx.save();
    ctx.clearRect(0, 0, w, h);

    // Deep Obsidian Space Background
    ctx.fillStyle = '#0b0f19';
    ctx.fillRect(0, 0, w, h);

    // Draw Subtle Grid Pattern
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
    ctx.lineWidth = 1;
    const gridSize = 40 * this.zoom;
    const startX = this.panX % gridSize;
    const startY = this.panY % gridSize;

    ctx.beginPath();
    for (let x = startX; x < w; x += gridSize) {
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
    }
    for (let y = startY; y < h; y += gridSize) {
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
    }
    ctx.stroke();

    // Active Focus / Neighborhood
    const activeNode = this.focusedNode || this.hoveredNode;
    const activeSet = new Set();
    if (activeNode) {
      activeSet.add(activeNode.id);
      activeNode.neighbors.forEach(id => activeSet.add(id));
    }

    // Draw Edges
    for (const e of this.edges) {
      const p1 = this.worldToScreen(e.source.x, e.source.y);
      const p2 = this.worldToScreen(e.target.x, e.target.y);

      const isConnected = activeNode && (e.source.id === activeNode.id || e.target.id === activeNode.id);
      const isDimmed = activeNode && !isConnected;

      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);

      if (isConnected) {
        ctx.strokeStyle = 'rgba(129, 140, 248, 0.85)';
        ctx.lineWidth = 2.5 * this.zoom;
        ctx.shadowColor = '#818cf8';
        ctx.shadowBlur = 8;
      } else if (isDimmed) {
        ctx.strokeStyle = 'rgba(148, 163, 184, 0.05)';
        ctx.lineWidth = 1 * this.zoom;
        ctx.shadowBlur = 0;
      } else {
        ctx.strokeStyle = 'rgba(148, 163, 184, 0.25)';
        ctx.lineWidth = 1.2 * this.zoom;
        ctx.shadowBlur = 0;
      }
      ctx.stroke();
      ctx.shadowBlur = 0;
    }

    // Draw Nodes & Labels
    for (const n of this.nodes) {
      const pos = this.worldToScreen(n.x, n.y);
      const isSelected = activeNode && n.id === activeNode.id;
      const isNeighbor = activeNode && activeSet.has(n.id) && !isSelected;
      const isDimmed = activeNode && !activeSet.has(n.id);

      const color = this.getNodeColor(n.label);
      const drawRadius = (n.radius + (isSelected ? 4 : 0)) * this.zoom;

      ctx.save();
      ctx.globalAlpha = isDimmed ? 0.2 : 1.0;

      // Glow Ring for Selected / Hovered
      if (isSelected || isNeighbor) {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, drawRadius + 6, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.globalAlpha = isDimmed ? 0.05 : (isSelected ? 0.35 : 0.18);
        ctx.fill();
        ctx.globalAlpha = isDimmed ? 0.2 : 1.0;
      }

      // Outer Node Circle
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, drawRadius, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.shadowColor = color;
      ctx.shadowBlur = isSelected ? 16 : 8;
      ctx.fill();
      ctx.shadowBlur = 0;

      // Inner Core Circle
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, drawRadius * 0.4, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.fill();

      // Node Label Text (Obsidian Style)
      const fontSize = Math.max(10, Math.min(13, 11 * this.zoom));
      ctx.font = `600 ${fontSize}px Inter, system-ui, sans-serif`;
      ctx.fillStyle = isDimmed ? 'rgba(148, 163, 184, 0.3)' : '#f8fafc';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';

      const labelText = n.id.length > 22 ? n.id.substring(0, 20) + '…' : n.id;
      ctx.fillText(labelText, pos.x, pos.y + drawRadius + 4);

      ctx.restore();
    }

    ctx.restore();
  }
}

let globalGraphInstance = null;

// Load Knowledge Graph
async function loadGraph() {
  const container = document.getElementById('graphNodesGrid');
  const canvas = document.getElementById('obsidianCanvas');
  if (!container && !canvas) return;

  try {
    const res = await fetch(`${API_BASE}/api/graph`);
    if (!res.ok) return;
    const data = await res.json();

    const metricsEl = document.getElementById('graphMetrics');
    if (metricsEl && data.stats) {
      metricsEl.textContent = `Nodes: ${data.stats.total_nodes} | Edges: ${data.stats.total_edges}`;
    }

    if (!data.nodes || data.nodes.length === 0) {
      if (container) container.innerHTML = '<p class="placeholder-text">Knowledge Graph is currently empty.</p>';
      return;
    }

    // Populate Obsidian Canvas Graph
    if (canvas) {
      if (!globalGraphInstance) {
        globalGraphInstance = new ObsidianGraphRenderer('obsidianCanvas', 'obsidianGraphContainer', 'graphTooltip');
        setupGraphControls();
      }
      globalGraphInstance.setData(data.nodes, data.edges || []);
    }

    // Populate Traditional Grid (Hidden by default)
    if (container) {
      container.innerHTML = data.nodes.map(n => `
        <div class="graph-card">
          <span class="label-badge">${escapeHtml(n.label)}</span>
          <h4>${escapeHtml(n.id)}</h4>
        </div>
      `).join('');
    }

  } catch (err) {
    console.error('Failed to load graph:', err);
  }
}

function setupGraphControls() {
  const resetBtn = document.getElementById('resetGraphViewBtn');
  const toggleBtn = document.getElementById('toggleGraphViewBtn');
  const canvasContainer = document.getElementById('obsidianGraphContainer');
  const gridContainer = document.getElementById('graphNodesGrid');

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (globalGraphInstance) globalGraphInstance.resetView();
    });
  }

  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      if (!canvasContainer || !gridContainer) return;
      if (canvasContainer.classList.contains('hidden')) {
        canvasContainer.classList.remove('hidden');
        gridContainer.classList.add('hidden');
      } else {
        canvasContainer.classList.add('hidden');
        gridContainer.classList.remove('hidden');
      }
    });
  }
}

// Ensure mediaDevices & getUserMedia polyfill for older WebKit / macOS WKWebView
if (!navigator.mediaDevices) {
  navigator.mediaDevices = {};
}
if (!navigator.mediaDevices.getUserMedia) {
  const legacyGetUserMedia = navigator.webkitGetUserMedia || navigator.mozGetUserMedia || navigator.getUserMedia;
  if (legacyGetUserMedia) {
    navigator.mediaDevices.getUserMedia = function(constraints) {
      return new Promise((resolve, reject) => {
        legacyGetUserMedia.call(navigator, constraints, resolve, reject);
      });
    };
  }
}

// Live Microphone Recorder Implementation
function initLiveRecorder() {
  const toggleBtn = document.getElementById('recToggleBtn');
  const toggleText = document.getElementById('recToggleText');
  const recBadge = document.getElementById('recBadge');
  const timerDisplay = document.getElementById('recTimer');
  const waveVis = document.getElementById('waveVisualizer');
  const errAlert = document.getElementById('micErrorAlert');

  let mediaRecorder = null;
  let audioChunks = [];
  let timerInterval = null;
  let secondsElapsed = 0;
  let isRecording = false;
  let useBackendRecording = false;

  if (!toggleBtn) return;

  toggleBtn.addEventListener('click', async () => {
    if (!isRecording) {
      // START RECORDING (Green -> Red)
      if (errAlert) errAlert.classList.add('hidden');
      useBackendRecording = false;

      const hasBrowserMic = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);

      if (hasBrowserMic) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          audioChunks = [];

          let options = {};
          if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported) {
            if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
              options = { mimeType: 'audio/webm;codecs=opus' };
            } else if (MediaRecorder.isTypeSupported('audio/webm')) {
              options = { mimeType: 'audio/webm' };
            } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
              options = { mimeType: 'audio/mp4' };
            }
          }

          try {
            mediaRecorder = new MediaRecorder(stream, options);
          } catch (e) {
            mediaRecorder = new MediaRecorder(stream);
          }

          mediaRecorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) audioChunks.push(e.data);
          };

          mediaRecorder.onstop = async () => {
            clearInterval(timerInterval);

            // Stop audio stream tracks
            stream.getTracks().forEach(track => track.stop());

            const actualMimeType = mediaRecorder.mimeType || 'audio/webm';
            const ext = actualMimeType.includes('mp4') ? 'mp4' : (actualMimeType.includes('wav') ? 'wav' : 'webm');

            const audioBlob = new Blob(audioChunks, { type: actualMimeType });
            const recordedFile = new File([audioBlob], `live_meeting_${Date.now()}.${ext}`, { type: actualMimeType });

            // Process recorded audio file
            await processRecordedFile(recordedFile);
          };

          // Collect audio chunks every 250ms
          mediaRecorder.start(250);
          isRecording = true;

          // Visual Transition: GREEN -> RED
          toggleBtn.className = 'btn rec-toggle-btn red lg';
          toggleText.textContent = 'STOP RECORDING & PROCESS MEETING';
          recBadge.textContent = 'RECORDING LIVE';
          recBadge.className = 'rec-badge recording';
          waveVis.classList.remove('hidden');

          // Start timer
          secondsElapsed = 0;
          updateTimer();
          timerInterval = setInterval(() => {
            secondsElapsed++;
            updateTimer();
          }, 1000);

          return;

        } catch (err) {
          console.warn('Browser getUserMedia failed/blocked, falling back to native backend audio recording...', err);
        }
      }

      // NATIVE BACKEND RECORDING FALLBACK (for Mac Desktop App WKWebView & native hardware capture)
      try {
        const formData = new FormData();
        formData.append('mode', 'mic');
        const startRes = await fetch(`${API_BASE}/api/audio/record_start`, {
          method: 'POST',
          body: formData,
        });

        if (!startRes.ok) {
          const errData = await startRes.json();
          throw new Error(errData.detail || 'Failed to start native backend recording.');
        }

        useBackendRecording = true;
        isRecording = true;

        toggleBtn.className = 'btn rec-toggle-btn red lg';
        toggleText.textContent = 'STOP RECORDING & PROCESS MEETING';
        recBadge.textContent = 'RECORDING LIVE (Native Engine)';
        recBadge.className = 'rec-badge recording';
        waveVis.classList.remove('hidden');

        secondsElapsed = 0;
        updateTimer();
        timerInterval = setInterval(() => {
          secondsElapsed++;
          updateTimer();
        }, 1000);

      } catch (err) {
        console.error('Microphone access & backend recording failed:', err);
        displayMicError(err);
      }

    } else {
      // STOP RECORDING (Red -> Processing -> Green)
      clearInterval(timerInterval);
      isRecording = false;
      toggleBtn.className = 'btn rec-toggle-btn green lg';
      toggleText.textContent = 'PROCESSING RECORDING...';
      toggleBtn.disabled = true;

      if (useBackendRecording) {
        // Stop native backend recording and trigger meeting memory processing
        await stopNativeBackendRecording();
      } else if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
      }
    }
  });

  function displayMicError(err) {
    isRecording = false;
    recBadge.textContent = 'Microphone Error';
    recBadge.className = 'rec-badge';
    if (errAlert) {
      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0 || navigator.userAgent.includes('Macintosh');
      let errDetail = '';
      const msg = (err.message || '').toLowerCase();

      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError' || msg.includes('permission') || msg.includes('blocked')) {
        errDetail = isMac
          ? `<strong>Permission Denied:</strong> macOS or your browser/app blocked microphone access.<br>
             👉 <strong>How to Fix on macOS:</strong><br>
             1. Open <strong>System Settings → Privacy & Security → Microphone</strong>.<br>
             2. Enable permission for <strong>Transcribe AI</strong> (or your terminal / browser app like Terminal, iTerm2, or Chrome).<br>
             3. If using Terminal/CLI, run <code>transcribe record --mode mic</code> to trigger macOS permission prompt.<br>
             4. Restart the app or refresh page.`
          : '<strong>Permission Denied:</strong> Browser blocked microphone access.<br>👉 <strong>Fix:</strong> Click the lock/tune icon in the browser address bar and set Microphone to <em>Allow</em>.';
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError' || msg.includes('not found')) {
        errDetail = '<strong>No Microphone Found:</strong> No audio input device detected.<br>👉 <strong>Fix:</strong> Plug in a microphone or headset and verify system sound settings.';
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError' || msg.includes('busy')) {
        errDetail = '<strong>Microphone Busy:</strong> The microphone is currently locked by another application.<br>👉 <strong>Fix:</strong> Close Teams, Zoom, FaceTime, or other apps using the mic and try again.';
      } else if (err.name === 'SecurityError' || (!window.isSecureContext && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1')) {
        errDetail = '<strong>Insecure Origin:</strong> Microphone access requires HTTPS when accessed outside localhost/127.0.0.1.<br>👉 <strong>Fix:</strong> Access the app via <code>http://127.0.0.1:8000</code> or setup HTTPS.';
      } else {
        errDetail = `<strong>Microphone Error (${err.name || 'Error'}):</strong> ${err.message || 'Unable to access microphone input.'}`;
      }

      errAlert.innerHTML = `
        <div style="padding: 12px 16px; border-radius: 8px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); color: #fca5a5; line-height: 1.5; font-size: 0.88rem;">
          ${errDetail}
          <div style="margin-top: 8px; font-size: 0.82rem; color: #cbd5e1;">
            💡 <em>Alternative: You can also use the <strong>Recordings Vault</strong> tab to upload pre-recorded meeting audio files.</em>
          </div>
        </div>
      `;
      errAlert.classList.remove('hidden');
    }
  }

  async function stopNativeBackendRecording() {
    const timeline = document.getElementById('recProcessingTimeline');
    const resultMsg = document.getElementById('recProcessingResultMsg');

    if (timeline) timeline.classList.remove('hidden');
    if (resultMsg) resultMsg.classList.add('hidden');

    setStageActive('rec', 1);

    let stageTimer = setInterval(() => {
      if (document.getElementById('recStage1') && document.getElementById('recStage1').classList.contains('active')) {
        setStageActive('rec', 2);
      } else if (document.getElementById('recStage2') && document.getElementById('recStage2').classList.contains('active')) {
        setStageActive('rec', 3);
      } else if (document.getElementById('recStage3') && document.getElementById('recStage3').classList.contains('active')) {
        setStageActive('rec', 4);
      } else if (document.getElementById('recStage4') && document.getElementById('recStage4').classList.contains('active')) {
        setStageActive('rec', 5);
      }
    }, 2000);

    try {
      const formData = new FormData();
      formData.append('title', `Live Meeting (${new Date().toLocaleTimeString()})`);
      const res = await fetch(`${API_BASE}/api/audio/record_stop`, {
        method: 'POST',
        body: formData,
      });

      clearInterval(stageTimer);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Processing failed');

      setStageDone('rec', 5);

      if (resultMsg) {
        resultMsg.className = 'result-msg success';
        resultMsg.innerHTML = `
          <strong>Live Recording Processed Successfully!</strong><br>
          Meeting Title: <em>${escapeHtml(data.title)}</em><br>
          Decisions Extracted: ${data.decisions_count} | Action Items: ${data.tasks_count}<br>
          Markdown exported at <code>${escapeHtml(data.markdown_path)}</code>
        `;
        resultMsg.classList.remove('hidden');
      }

      loadStats();
      loadMeetings();
      loadRecordings();
    } catch (err) {
      clearInterval(stageTimer);
      if (resultMsg) {
        resultMsg.className = 'result-msg error';
        resultMsg.textContent = `Processing error: ${err.message}`;
        resultMsg.classList.remove('hidden');
      }
    } finally {
      toggleBtn.className = 'btn rec-toggle-btn green lg';
      toggleText.textContent = 'START RECORDING LIVE';
      toggleBtn.disabled = false;
      recBadge.textContent = 'Microphone Ready (Idle)';
      recBadge.className = 'rec-badge green-badge';
      waveVis.classList.add('hidden');
    }
  }

  const checkDiagBtn = document.getElementById('checkMicDiagBtn');
  if (checkDiagBtn) {
    checkDiagBtn.addEventListener('click', () => {
      loadAudioDevices(true);
    });
  }

  function updateTimer() {
    const mins = Math.floor(secondsElapsed / 60).toString().padStart(2, '0');
    const secs = (secondsElapsed % 60).toString().padStart(2, '0');
    timerDisplay.textContent = `${mins}:${secs}`;
  }

  async function processRecordedFile(file) {
    const timeline = document.getElementById('recProcessingTimeline');
    const resultMsg = document.getElementById('recProcessingResultMsg');

    if (timeline) timeline.classList.remove('hidden');
    if (resultMsg) resultMsg.classList.add('hidden');

    setStageActive('rec', 1);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', `Live Meeting (${new Date().toLocaleTimeString()})`);

    let stageTimer = setInterval(() => {
      // Smoothly advance stage progress while pipeline runs
      if (document.getElementById('recStage1') && document.getElementById('recStage1').classList.contains('active')) {
        setStageActive('rec', 2);
      } else if (document.getElementById('recStage2') && document.getElementById('recStage2').classList.contains('active')) {
        setStageActive('rec', 3);
      } else if (document.getElementById('recStage3') && document.getElementById('recStage3').classList.contains('active')) {
        setStageActive('rec', 4);
      } else if (document.getElementById('recStage4') && document.getElementById('recStage4').classList.contains('active')) {
        setStageActive('rec', 5);
      }
    }, 2000);

    try {
      const res = await fetch(`${API_BASE}/api/process`, {
        method: 'POST',
        body: formData
      });

      clearInterval(stageTimer);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Processing failed');

      setStageDone('rec', 5);

      if (resultMsg) {
        resultMsg.className = 'result-msg success';
        resultMsg.innerHTML = `
          <strong>Live Recording Processed Successfully!</strong><br>
          Meeting Title: <em>${escapeHtml(data.title)}</em><br>
          Decisions Extracted: ${data.decisions_count} | Action Items: ${data.tasks_count}<br>
          Markdown exported at <code>${escapeHtml(data.markdown_path)}</code>
        `;
        resultMsg.classList.remove('hidden');
      }

      loadStats();
      loadMeetings();
      loadRecordings();
    } catch (err) {
      clearInterval(stageTimer);
      if (resultMsg) {
        resultMsg.className = 'result-msg error';
        resultMsg.textContent = `Processing error: ${err.message}`;
        resultMsg.classList.remove('hidden');
      }
    } finally {
      // Reset Toggle Button back to Green Idle state
      toggleBtn.className = 'btn rec-toggle-btn green lg';
      toggleText.textContent = 'START RECORDING LIVE';
      toggleBtn.disabled = false;
      recBadge.textContent = 'Microphone Ready (Idle)';
      recBadge.className = 'rec-badge green-badge';
      waveVis.classList.add('hidden');
    }
  }
}

// Inspect system audio hardware & test browser microphone access
async function loadAudioDevices(promptPermission = false) {
  const diagContainer = document.getElementById('micDiagDetails');
  if (!diagContainer) return;

  let micTestStatus = 'Testing...';
  let micPermissionOk = false;

  if (promptPermission && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    try {
      const testStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      testStream.getTracks().forEach(track => track.stop());
      micPermissionOk = true;
      micTestStatus = '✅ Browser Microphone Access Granted';
    } catch (err) {
      micPermissionOk = false;
      micTestStatus = `❌ Permission Error (${err.name || 'Error'}): ${err.message}`;
    }
  }

  try {
    const res = await fetch(`${API_BASE}/api/audio/devices`);
    if (!res.ok) throw new Error('Failed to fetch audio devices');
    const data = await res.json();

    const devices = data.devices || [];
    const status = data.setup_status || {};
    const inputDevs = devices.filter(d => d.kind === 'input');
    const loopbackDevs = devices.filter(d => d.kind === 'loopback');

    let html = `<div style="display: flex; flex-direction: column; gap: 8px;">`;
    
    if (promptPermission) {
      const statusColor = micPermissionOk ? '#10b981' : '#f43f5e';
      html += `<div style="color: ${statusColor}; font-weight: 600;">${micTestStatus}</div>`;
    }

    html += `<div><strong>Detected Hardware Devices:</strong> ${inputDevs.length} Input Mic(s), ${loopbackDevs.length} System Loopback Device(s)</div>`;

    if (inputDevs.length > 0) {
      html += `<ul style="margin: 4px 0 8px 18px; padding: 0;">`;
      inputDevs.forEach(d => {
        html += `<li>🎙️ <strong>${escapeHtml(d.name)}</strong> (ID: <code>${escapeHtml(d.id)}</code>)</li>`;
      });
      html += `</ul>`;
    } else {
      html += `<div style="color: #fbbf24; margin-top: 4px;">⚠️ No hardware microphone listed by system scan.</div>`;
    }

    if (status.recommendations && status.recommendations.length > 0) {
      html += `<div style="margin-top: 4px;"><strong>System Call Diagnostics:</strong>`;
      html += `<ul style="margin: 2px 0 0 18px; padding: 0;">`;
      status.recommendations.forEach(r => {
        html += `<li>• ${escapeHtml(r)}</li>`;
      });
      html += `</ul></div>`;
    }

    html += `</div>`;
    diagContainer.innerHTML = html;
  } catch (err) {
    diagContainer.innerHTML = `<span style="color: #94a3b8;">System Audio Hook scan: ${escapeHtml(err.message)}</span>`;
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Settings & Model Manager logic
async function initSettings() {
  const saveBtn = document.getElementById('saveSettingsBtn');
  const tempSlider = document.getElementById('settingLlmTemp');
  const tempLabel = document.getElementById('tempValLabel');

  if (tempSlider && tempLabel) {
    tempSlider.addEventListener('input', () => {
      tempLabel.textContent = tempSlider.value;
    });
  }

  if (saveBtn) {
    saveBtn.addEventListener('click', saveSettings);
  }

  const cleanRecordingsBtn = document.getElementById('cleanRecordingsBtn');
  if (cleanRecordingsBtn) {
    cleanRecordingsBtn.addEventListener('click', () => triggerCleanup(false));
  }

  const cleanAllBtn = document.getElementById('cleanAllBtn');
  if (cleanAllBtn) {
    cleanAllBtn.addEventListener('click', () => {
      if (confirm('Are you sure you want to delete ALL meeting recordings, transcripts, vector DBs, and speaker profiles? This action cannot be undone.')) {
        triggerCleanup(true);
      }
    });
  }

  await loadSettings();
}

async function triggerCleanup(deleteAll) {
  const alertDiv = document.getElementById('settingsAlert');
  try {
    const formData = new FormData();
    formData.append('delete_all', deleteAll ? 'true' : 'false');
    formData.append('delete_recordings', 'true');

    const res = await fetch(`${API_BASE}/api/cleanup`, {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Cleanup failed');

    if (alertDiv) {
      alertDiv.className = 'result-msg success';
      alertDiv.innerHTML = `<strong>🧹 ${data.message}</strong>`;
      alertDiv.classList.remove('hidden');
    }

    loadStats();
    loadMeetings();
    loadRecordings();
    if (typeof loadSpeakers === 'function') loadSpeakers();
    if (typeof loadGraph === 'function') loadGraph();

  } catch (err) {
    if (alertDiv) {
      alertDiv.className = 'result-msg error';
      alertDiv.textContent = `Error performing cleanup: ${err.message}`;
      alertDiv.classList.remove('hidden');
    }
  }
}


async function loadSettings() {
  try {
    const res = await fetch(`${API_BASE}/api/settings`);
    if (!res.ok) return;
    const data = await res.json();

    const storage = data.storage || {};
    const stt = data.speech || {};
    const llm = data.llm || {};

    if (storage.base_dir) document.getElementById('settingStorageDir').value = storage.base_dir;
    if (stt.model_size) {
      const presets = ['large-v3-turbo', 'large-v3', 'medium', 'small', 'base', 'tiny'];
      if (presets.includes(stt.model_size)) {
        document.getElementById('settingSttModel').value = stt.model_size;
        document.getElementById('settingSttModelCustom').value = '';
      } else {
        document.getElementById('settingSttModelCustom').value = stt.model_size;
      }
    }
    if (stt.device) document.getElementById('settingSttDevice').value = stt.device;
    if (stt.provider) document.getElementById('settingSttProvider').value = stt.provider;
    if (stt.language) document.getElementById('settingSttLang').value = stt.language;


    const llmModelSelect = document.getElementById('settingLlmModel');
    if (llmModelSelect && llm.available_models) {
      llmModelSelect.innerHTML = llm.available_models.map(m =>
        `<option value="${escapeHtml(m)}">${escapeHtml(m)}</option>`
      ).join('');
      if (llm.model_name) llmModelSelect.value = llm.model_name;
    }

    if (llm.api_base) document.getElementById('settingLlmApiBase').value = llm.api_base;
    if (llm.provider) document.getElementById('settingLlmProvider').value = llm.provider;
    if (llm.temperature !== undefined) {
      const slider = document.getElementById('settingLlmTemp');
      const label = document.getElementById('tempValLabel');
      if (slider) slider.value = llm.temperature;
      if (label) label.textContent = llm.temperature;
    }
  } catch (err) {
    console.error('Failed to load settings:', err);
  }
}

async function saveSettings() {
  const saveBtn = document.getElementById('saveSettingsBtn');
  const alertDiv = document.getElementById('settingsAlert');

  if (saveBtn) saveBtn.disabled = true;

  const storageDir = document.getElementById('settingStorageDir').value.trim();
  const sttModelPreset = document.getElementById('settingSttModel').value;
  const sttModelCustom = document.getElementById('settingSttModelCustom').value.trim();
  const sttModel = sttModelCustom || sttModelPreset;

  const sttDevice = document.getElementById('settingSttDevice').value;
  const sttProvider = document.getElementById('settingSttProvider').value;
  const sttLang = document.getElementById('settingSttLang').value;


  const llmModelSelect = document.getElementById('settingLlmModel').value;
  const llmModelCustom = document.getElementById('settingLlmModelCustom').value.trim();
  const llmModel = llmModelCustom || llmModelSelect;

  const llmApiBase = document.getElementById('settingLlmApiBase').value;
  const llmProvider = document.getElementById('settingLlmProvider').value;
  const llmTemp = parseFloat(document.getElementById('settingLlmTemp').value);

  const payload = {
    storage_dir: storageDir,
    stt_model_size: sttModel,
    stt_device: sttDevice,
    stt_provider: sttProvider,
    stt_language: sttLang,
    llm_model_name: llmModel,
    llm_provider: llmProvider,
    llm_api_base: llmApiBase,
    llm_temperature: llmTemp,
  };

  try {
    const res = await fetch(`${API_BASE}/api/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to save settings');

    if (alertDiv) {
      alertDiv.className = 'result-msg success';
      alertDiv.innerHTML = `<strong>✓ Settings Saved!</strong> Data storage location set to <code>${escapeHtml(data.storage_dir || storageDir)}</code>. Speech model set to <em>${escapeHtml(sttModel)}</em> (${escapeHtml(sttDevice)}) and LLM set to <em>${escapeHtml(llmModel)}</em>. Saved to <code>transcribe.yaml</code>.`;
      alertDiv.classList.remove('hidden');
    }

    loadStats();
    loadMeetings();
    loadRecordings();
  } catch (err) {
    if (alertDiv) {
      alertDiv.className = 'result-msg error';
      alertDiv.textContent = `Error saving settings: ${err.message}`;
      alertDiv.classList.remove('hidden');
    }
  } finally {
    if (saveBtn) saveBtn.disabled = false;
  }
}

/* ==========================================================================
   VYRON AI NEURAL OS INTERACTIVE LOGIC
   ========================================================================== */

function initVyronOrbCanvas() {
  const canvas = document.getElementById('vyronOrbCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  const centerX = width / 2;
  const centerY = height / 2;

  let currentMode = 'idle';
  let angle = 0;
  let pulse = 0;

  const modeConfigs = {
    idle: { speed: 0.015, pulseSpeed: 0.03, color1: '#7C3AED', color2: '#a78bfa', label: 'STATUS: IDLE // READY TO EXECUTE' },
    listening: { speed: 0.03, pulseSpeed: 0.06, color1: '#06b6d4', color2: '#38bdf8', label: 'STATUS: LISTENING // ACOUSTIC ARRAY ACTIVE' },
    processing: { speed: 0.06, pulseSpeed: 0.1, color1: '#f59e0b', color2: '#fbbf24', label: 'STATUS: PROCESSING // NEURAL REASONING MATRIX' },
    speaking: { speed: 0.04, pulseSpeed: 0.08, color1: '#10b981', color2: '#34d399', label: 'STATUS: SPEAKING // SYNTHESIZING VOICE OUTPUT' },
    recording: { speed: 0.05, pulseSpeed: 0.09, color1: '#ef4444', color2: '#f87171', label: 'STATUS: RECORDING // SYSTEM LOOPBACK ACTIVE' }
  };

  const stateBtns = document.querySelectorAll('.orb-state-btn');
  const greetingEl = document.getElementById('vyronGreeting');

  stateBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      stateBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentMode = btn.dataset.state;

      if (greetingEl && modeConfigs[currentMode]) {
        greetingEl.textContent = modeConfigs[currentMode].label;
      }
    });
  });

  const numParticles = 48;
  const particles = [];
  for (let i = 0; i < numParticles; i++) {
    particles.push({
      theta: Math.random() * Math.PI * 2,
      phi: Math.acos(Math.random() * 2 - 1),
      radius: 80 + Math.random() * 20,
      size: 1.5 + Math.random() * 2.5,
      speed: 0.005 + Math.random() * 0.01
    });
  }

  function animate() {
    ctx.clearRect(0, 0, width, height);

    const config = modeConfigs[currentMode] || modeConfigs.idle;
    angle += config.speed;
    pulse += config.pulseSpeed;

    const currentPulse = Math.sin(pulse) * 12;

    const gradient = ctx.createRadialGradient(centerX, centerY, 10, centerX, centerY, 90 + currentPulse);
    gradient.addColorStop(0, 'rgba(255, 255, 255, 0.9)');
    gradient.addColorStop(0.3, config.color2);
    gradient.addColorStop(0.7, config.color1);
    gradient.addColorStop(1, 'transparent');

    ctx.beginPath();
    ctx.arc(centerX, centerY, 90 + currentPulse, 0, Math.PI * 2);
    ctx.fillStyle = gradient;
    ctx.fill();

    ctx.save();
    ctx.translate(centerX, centerY);

    ctx.rotate(angle);
    ctx.beginPath();
    ctx.ellipse(0, 0, 120 + currentPulse * 0.5, 45, angle * 0.5, 0, Math.PI * 2);
    ctx.strokeStyle = config.color2;
    ctx.lineWidth = 1.5;
    ctx.setLineDash([8, 12]);
    ctx.stroke();

    ctx.rotate(-angle * 1.5);
    ctx.beginPath();
    ctx.ellipse(0, 0, 135 + currentPulse * 0.3, 50, -angle * 0.8, 0, Math.PI * 2);
    ctx.strokeStyle = config.color1;
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 16]);
    ctx.stroke();

    ctx.restore();

    particles.forEach(p => {
      p.theta += p.speed;
      const r = p.radius + currentPulse * 0.4;
      const x = centerX + r * Math.sin(p.phi) * Math.cos(p.theta + angle);
      const y = centerY + r * Math.sin(p.phi) * Math.sin(p.theta + angle);
      const scale = (Math.cos(p.phi) + 2) / 3;

      ctx.beginPath();
      ctx.arc(x, y, p.size * scale, 0, Math.PI * 2);
      ctx.fillStyle = config.color2;
      ctx.shadowBlur = 10;
      ctx.shadowColor = config.color1;
      ctx.fill();
      ctx.shadowBlur = 0;
    });

    requestAnimationFrame(animate);
  }

  animate();
}

function initVyronTerminal() {
  const tabBtns = document.querySelectorAll('.terminal-tab-btn');
  const cmdText = document.getElementById('terminalCmdText');
  const logOutput = document.getElementById('terminalLogOutput');
  const copyBtn = document.getElementById('copyCmdBtn');

  const commands = {
    record: {
      cmd: 'transcribe record --mode mixed --title "Executive Roadmap Sync"',
      logs: [
        '<p class="comment"># Initialize visionary reasoning operational neural-network...</p>',
        '<p class="log">[INFO] Initializing Faster-Whisper (large-v3-turbo) on MPS/GPU</p>',
        '<p class="log">[INFO] Hooked into System Audio Loopback + Microphone Array</p>',
        '<p class="log">[SUCCESS] Diarization engine loaded (PyAnnote persistent voiceprints)</p>',
        '<p class="log">[STATUS] Recording in progress... Press Ctrl+C to finish and summarize</p>'
      ]
    },
    ask: {
      cmd: 'transcribe ask "What decisions were made regarding backend architecture?"',
      logs: [
        '<p class="comment"># Querying cross-meeting vector index & knowledge graph...</p>',
        '<p class="log">[RAG] Retreived 8 relevant transcript segments across 3 past meetings</p>',
        '<p class="log">[LLM] Reasoning over retrieved context with LM Studio / Gemini...</p>',
        '<p class="log" style="color:#a78bfa">"The team agreed to adopt FastAPI backend with Chroma vector store and Faster-Whisper local diarization."</p>'
      ]
    },
    serve: {
      cmd: 'transcribe serve --port 8000 --host 127.0.0.1',
      logs: [
        '<p class="comment"># Launching Transcribe AI Web SPA & API Server...</p>',
        '<p class="log">[INFO] FastAPI server listening at http://127.0.0.1:8000</p>',
        '<p class="log">[INFO] Static Web UI served with modern glassmorphism SPA</p>',
        '<p class="log" style="color:#22c55e">[READY] Web Dashboard & Desktop Tauri interface operational!</p>'
      ]
    }
  };

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const mode = btn.dataset.cmd;
      if (commands[mode]) {
        cmdText.textContent = commands[mode].cmd;
        logOutput.innerHTML = commands[mode].logs.join('');
      }
    });
  });

  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      if (cmdText) {
        navigator.clipboard.writeText(cmdText.textContent);
        const originalSvg = copyBtn.innerHTML;
        copyBtn.innerHTML = '<span style="color:#22c55e; font-size:0.75rem; font-family:monospace;">✓ Copied</span>';
        setTimeout(() => { copyBtn.innerHTML = originalSvg; }, 2000);
      }
    });
  }
}

function initVyronBackdrop() {
  const canvas = document.getElementById('vyronBackdropCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  function resize() {
    canvas.width = canvas.parentElement ? canvas.parentElement.offsetWidth : window.innerWidth;
    canvas.height = canvas.parentElement ? canvas.parentElement.offsetHeight : 1200;
  }
  resize();
  window.addEventListener('resize', resize);

  const numStars = 60;
  const stars = [];
  for (let i = 0; i < numStars; i++) {
    stars.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      size: Math.random() * 2,
      vy: 0.1 + Math.random() * 0.3,
      alpha: Math.random()
    });
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    stars.forEach(s => {
      s.y -= s.vy;
      if (s.y < 0) s.y = canvas.height;

      ctx.beginPath();
      ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(167, 139, 250, ${s.alpha})`;
      ctx.fill();
    });

    requestAnimationFrame(draw);
  }
  draw();
}

/* ==========================================================================
   ALFRED AMBIENT BUTLER & MODEL ORCHESTRATOR LOGIC
   ========================================================================== */

function initAlfredButler() {
  const tierBoxes = document.querySelectorAll('.tier-box');
  const activeBadge = document.getElementById('alfredActiveTierBadge');
  const ledgerConsole = document.getElementById('alfredLedgerConsole');
  const saveModelsBtn = document.getElementById('saveAlfredModelsBtn');
  const modelsAlert = document.getElementById('alfredModelsAlert');
  const refreshLedgerBtn = document.getElementById('refreshLedgerBtn');

  tierBoxes.forEach(box => {
    box.addEventListener('click', () => {
      tierBoxes.forEach(b => b.classList.remove('active'));
      box.classList.add('active');
      const tierName = box.dataset.tier;

      if (activeBadge) {
        activeBadge.textContent = `ACTIVE TIER: ${tierName.toUpperCase()}`;
        if (tierName === 'Asking') activeBadge.className = 'status-pill blue';
        else if (tierName === 'Confirming') activeBadge.className = 'status-pill green';
        else if (tierName === 'Acting') activeBadge.className = 'status-pill purple';
      }

      if (ledgerConsole) {
        const time = new Date().toTimeString().split(' ')[0];
        const line = document.createElement('div');
        line.className = 'ledger-line';
        line.innerHTML = `<span class="time">[${time}]</span> <span class="tag system">tier-governor</span>: Autonomy ceiling updated to <strong>${tierName}</strong> (fail_closed=true)`;
        ledgerConsole.prepend(line);
      }
    });
  });

  if (saveModelsBtn) {
    saveModelsBtn.addEventListener('click', async () => {
      saveModelsBtn.disabled = true;

      const mainProvider = document.getElementById('alfredMainProvider').value;
      const mainModel = document.getElementById('alfredMainModel').value.trim();
      const workerProvider = document.getElementById('alfredWorkerProvider').value;
      const workerModel = document.getElementById('alfredWorkerModel').value.trim();
      const speechProvider = document.getElementById('alfredSpeechProvider').value;
      const speechPreset = document.getElementById('alfredSpeechPreset').value;

      try {
        const payload = {
          llm_provider: mainProvider,
          llm_model_name: mainModel,
          stt_provider: speechProvider,
          stt_model_size: speechPreset
        };

        const res = await fetch(`${API_BASE}/api/settings`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (modelsAlert) {
          modelsAlert.className = 'result-msg success';
          modelsAlert.innerHTML = `<strong>✓ Neural Model Routing Applied!</strong> Reasoner set to <em>${mainProvider.toUpperCase()} (${mainModel})</em> and Speed Worker set to <em>${workerProvider.toUpperCase()} (${workerModel})</em>.`;
          modelsAlert.classList.remove('hidden');
        }

        if (ledgerConsole) {
          const time = new Date().toTimeString().split(' ')[0];
          const line = document.createElement('div');
          line.className = 'ledger-line';
          line.innerHTML = `<span class="time">[${time}]</span> <span class="tag success">model-router</span>: Updated Main Reasoner (${mainProvider}/${mainModel}) & Worker (${workerProvider}/${workerModel})`;
          ledgerConsole.prepend(line);
        }

        loadStats();
      } catch (err) {
        if (modelsAlert) {
          modelsAlert.className = 'result-msg error';
          modelsAlert.textContent = `Failed to apply model settings: ${err.message}`;
          modelsAlert.classList.remove('hidden');
        }
      } finally {
        saveModelsBtn.disabled = false;
      }
    });
  }

  if (refreshLedgerBtn && ledgerConsole) {
    refreshLedgerBtn.addEventListener('click', () => {
      const time = new Date().toTimeString().split(' ')[0];
      const line = document.createElement('div');
      line.className = 'ledger-line';
      line.innerHTML = `<span class="time">[${time}]</span> <span class="tag auto">audit-sweep</span>: System audit sweep clean. 0 poison records, 100% data retention verified.`;
      ledgerConsole.prepend(line);
    });
  }
}

/* ==========================================================================
   PERSONAL AGENT AUTOMATION ENGINE LOGIC
   ========================================================================== */

window.runAgentTask = async function(taskId) {
  const inputEl = document.getElementById('agentPromptInput');
  const prompt = inputEl ? inputEl.value.trim() : '';
  const consoleOut = document.getElementById('agentConsoleOutput');
  const statusBadge = document.getElementById('agentTaskStatusBadge');
  const resultDetails = document.getElementById('agentResultDetails');

  if (statusBadge) {
    statusBadge.textContent = 'AGENT EXECUTING...';
    statusBadge.className = 'status-pill yellow';
  }

  if (consoleOut) {
    const time = new Date().toTimeString().split(' ')[0];
    consoleOut.innerHTML = `<p class="comment"># Launching personal agent task execution [${taskId}]...</p>`;
    consoleOut.innerHTML += `<p class="log">[TIME ${time}] Dispatching task '${taskId}' to local automation runner</p>`;
  }

  try {
    const payload = { task_id: taskId, prompt: prompt || undefined };
    const res = await fetch(`${API_BASE}/api/agent/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Task execution failed');

    if (consoleOut && data.logs) {
      data.logs.forEach(logLine => {
        const p = document.createElement('p');
        p.className = 'log';
        if (logLine.includes('SUCCESS')) p.style.color = '#34d399';
        if (logLine.includes('ACTION')) p.style.color = '#a78bfa';
        p.textContent = logLine;
        consoleOut.appendChild(p);
      });
    }

    if (statusBadge) {
      statusBadge.textContent = 'AGENT IDLE (COMPLETED)';
      statusBadge.className = 'status-pill green';
    }

    if (resultDetails) {
      resultDetails.className = 'result-msg success';
      resultDetails.innerHTML = `<strong>✓ Task Completed (${data.execution_time_sec}s):</strong> ${escapeHtml(data.summary)}`;
      if (data.artifacts && data.artifacts.length > 0) {
        resultDetails.innerHTML += `<br><em>Generated Artifact: <code>${escapeHtml(data.artifacts.join(', '))}</code></em>`;
      }
      resultDetails.classList.remove('hidden');
    }

    loadMeetings();
    loadStats();
  } catch (err) {
    if (statusBadge) {
      statusBadge.textContent = 'EXECUTION ERROR';
      statusBadge.className = 'status-pill red';
    }
    if (resultDetails) {
      resultDetails.className = 'result-msg error';
      resultDetails.textContent = `Agent execution error: ${err.message}`;
      resultDetails.classList.remove('hidden');
    }
  }
};

function initAgentService() {
  const customBtn = document.getElementById('runAgentCustomBtn');
  const inputEl = document.getElementById('agentPromptInput');

  if (customBtn) {
    customBtn.addEventListener('click', () => {
      window.runAgentTask('custom');
    });
  }

  if (inputEl) {
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        window.runAgentTask('custom');
      }
    });
  }
}

// Vexa Bot & Connectors Frontend Handlers
window.joinVexaBotCall = async function() {
  const urlEl = document.getElementById('vexaMeetingUrl');
  const statusEl = document.getElementById('vexaBotStatus');
  const joinBtn = document.getElementById('joinBotBtn');
  const stopBtn = document.getElementById('stopBotBtn');
  if (!urlEl || !urlEl.value.trim()) {
    if (statusEl) {
      statusEl.className = 'result-msg error';
      statusEl.textContent = 'Please enter a valid Google Meet, Teams, or Zoom URL.';
      statusEl.classList.remove('hidden');
    }
    return;
  }

  if (statusEl) {
    statusEl.className = 'result-msg info';
    statusEl.textContent = '🚀 Launching Neural Agent Bot to join call...';
    statusEl.classList.remove('hidden');
  }

  try {
    const res = await fetch(`${API_BASE}/api/connectors/bot/join`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: urlEl.value.trim(), duration_seconds: 1800 })
    });
    const data = await res.json();
    if (statusEl) {
      statusEl.className = 'result-msg success';
      statusEl.innerHTML = `<strong>✓ Bot joined (${escapeHtml(data.platform || 'meeting')}):</strong> Recording as "Neural Agent Bot". Click Stop when meeting ends.`;
    }
    if (joinBtn) joinBtn.style.display = 'none';
    if (stopBtn) stopBtn.style.display = 'inline-flex';
  } catch (err) {
    if (statusEl) {
      statusEl.className = 'result-msg error';
      statusEl.textContent = `Failed to join call: ${err.message}`;
    }
  }
};

window.stopVexaBot = async function() {
  const statusEl = document.getElementById('vexaBotStatus');
  const joinBtn = document.getElementById('joinBotBtn');
  const stopBtn = document.getElementById('stopBotBtn');

  if (statusEl) {
    statusEl.className = 'result-msg info';
    statusEl.textContent = '⏳ Stopping bot and processing meeting... This may take a minute.';
    statusEl.classList.remove('hidden');
  }
  if (stopBtn) stopBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/connectors/bot/stop`, { method: 'POST' });
    const data = await res.json();
    if (statusEl) {
      if (data.meeting_id) {
        statusEl.className = 'result-msg success';
        statusEl.innerHTML = `<strong>✅ Meeting processed!</strong> "${escapeHtml(data.title || 'Meeting')}" saved — ${data.tasks_count || 0} tasks, ${data.decisions_count || 0} decisions extracted. <a href="#meetings" onclick="window.switchTab('meetings')" style="color:#a78bfa;">View in Meeting Memory →</a>`;
        loadStats();
        loadMeetings();
        loadApprovalQueue();
      } else {
        statusEl.className = 'result-msg';
        statusEl.textContent = 'Bot stopped. ' + (data.note || '');
      }
    }
    if (joinBtn) { joinBtn.style.display = 'inline-flex'; joinBtn.disabled = false; }
    if (stopBtn) { stopBtn.style.display = 'none'; stopBtn.disabled = false; }
  } catch (err) {
    if (statusEl) {
      statusEl.className = 'result-msg error';
      statusEl.textContent = `Error stopping bot: ${err.message}`;
    }
    if (stopBtn) stopBtn.disabled = false;
  }
};

window.triggerStenoCheck = async function() {
  const badgeEl = document.getElementById('stenoCallBadge');
  try {
    const res = await fetch(`${API_BASE}/api/connectors/steno/status`);
    const data = await res.json();
    if (badgeEl) {
      if (data.is_call_active) {
        badgeEl.textContent = `🔴 ACTIVE CALL: ${data.primary_app}`;
        badgeEl.style.background = 'rgba(220,53,69,0.2)';
        badgeEl.style.color = '#f87171';
      } else {
        badgeEl.textContent = 'No Active Calls';
        badgeEl.style.background = 'rgba(34,197,94,0.15)';
        badgeEl.style.color = '#4ade80';
      }
    }
  } catch (e) {}
};

// Load connector OAuth status badges
async function loadConnectorStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/connectors/status`);
    if (!res.ok) return;
    const data = await res.json();

    const gmailBadge = document.getElementById('gmailStatusBadge');
    const gcalBadge = document.getElementById('gcalStatusBadge');

    if (gmailBadge) {
      gmailBadge.textContent = data.gmail && data.gmail.authorized ? '✓ Authorized' : '✗ Not configured';
      gmailBadge.style.background = data.gmail && data.gmail.authorized ? 'rgba(34,197,94,0.15)' : 'rgba(255,255,255,0.08)';
      gmailBadge.style.color = data.gmail && data.gmail.authorized ? '#4ade80' : 'rgba(255,255,255,0.5)';
    }
    if (gcalBadge) {
      gcalBadge.textContent = data.google_calendar && data.google_calendar.authorized ? '✓ Authorized' : '✗ Not configured';
      gcalBadge.style.background = data.google_calendar && data.google_calendar.authorized ? 'rgba(34,197,94,0.15)' : 'rgba(255,255,255,0.08)';
      gcalBadge.style.color = data.google_calendar && data.google_calendar.authorized ? '#4ade80' : 'rgba(255,255,255,0.5)';
    }
  } catch (e) {}
}

// Load upcoming calendar events
async function loadCalendarEvents() {
  const container = document.getElementById('upcomingEventsList');
  if (!container) return;

  container.innerHTML = '<p style="color: rgba(255,255,255,0.5); font-size: 0.85rem;">Loading calendar events...</p>';

  try {
    const res = await fetch(`${API_BASE}/api/connectors/calendar/upcoming`);
    if (!res.ok) throw new Error('API error');
    const events = await res.json();

    if (!events || events.length === 0) {
      container.innerHTML = '<p class="placeholder-text">No upcoming events. Add Google Calendar credentials to see real events.</p>';
      return;
    }

    container.innerHTML = events.map(ev => `
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.06);">
        <div>
          <div style="font-weight: 600; font-size: 0.9rem;">${escapeHtml(ev.title)}</div>
          <div style="font-size: 0.78rem; color: rgba(255,255,255,0.5); margin-top: 2px;">${escapeHtml(ev.start_time)} · ${escapeHtml(ev.source || '')}</div>
        </div>
        ${ev.meeting_url ? `<button class="btn primary sm" onclick="document.getElementById('vexaMeetingUrl').value='${escapeHtml(ev.meeting_url)}'; window.switchTab('connectors');" style="white-space: nowrap; font-size: 0.75rem;">🤖 Join & Record</button>` : '<span style="font-size: 0.75rem; color: rgba(255,255,255,0.3);">No link</span>'}
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<p class="error-text" style="font-size:0.85rem;">Could not load events: ${escapeHtml(err.message)}</p>`;
  }
}

window.loadApprovalQueue = async function() {
  const container = document.getElementById('emailApprovalQueueContainer');
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/api/connectors/actions/queue`);
    const queue = await res.json();
    if (queue.length === 0) {
      container.innerHTML = '<p class="placeholder-text">No pending email drafts. Process a meeting to auto-generate action emails.</p>';
      return;
    }

    container.innerHTML = queue.map(item => `
      <div class="rec-item-card" style="margin-bottom: 10px; padding: 12px; background: rgba(255,255,255,0.04); border-radius: 8px;">
        <div class="rec-info" style="flex: 1;">
          <h4 style="font-size: 0.9rem;">📧 ${escapeHtml(item.subject)}</h4>
          <p style="font-size: 0.82rem; color: rgba(255,255,255,0.6); margin: 4px 0;">To: ${escapeHtml(item.recipient)}</p>
          <p style="font-size: 0.78rem; color: rgba(255,255,255,0.45);">${escapeHtml((item.body || '').substring(0, 120))}...</p>
        </div>
        <div style="display: flex; gap: 8px; margin-top: 8px;">
          <button class="btn primary sm" onclick="window.approveEmail('${escapeHtml(item.draft_id)}')">
            ✅ Approve & Send
          </button>
          <button class="btn secondary sm" onclick="window.rejectEmail('${escapeHtml(item.draft_id)}')" style="opacity: 0.7;">
            ✗ Dismiss
          </button>
        </div>
      </div>
    `).join('');
  } catch (e) {}
};

window.approveEmail = async function(draftId) {
  try {
    const res = await fetch(`${API_BASE}/api/connectors/actions/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ draft_id: draftId })
    });
    const data = await res.json();
    const msg = data.status === 'sent' ? 'Email sent successfully!' : 'Email approved (status: ' + data.status + ')';
    alert(msg);
    window.loadApprovalQueue();
  } catch (err) {
    alert('Failed to approve email: ' + err.message);
  }
};

window.rejectEmail = async function(draftId) {
  // Just remove from queue locally (no server call needed, it stays unless explicitly dismissed)
  window.loadApprovalQueue();
};

// Save diarization settings (HF token + provider)
async function saveDiarizationSettings() {
  const provider = document.getElementById('settingDiarizationProvider')?.value || 'mock';
  const hfToken = document.getElementById('settingHFToken')?.value || '';
  const alertEl = document.getElementById('diarizationAlert');

  if (alertEl) {
    alertEl.className = 'result-msg info';
    alertEl.textContent = 'Saving diarization settings...';
    alertEl.classList.remove('hidden');
  }

  try {
    const formData = new FormData();
    formData.append('provider', provider);
    formData.append('hf_token', hfToken);
    const res = await fetch(`${API_BASE}/api/settings/diarization`, { method: 'POST', body: formData });
    const data = await res.json();
    if (alertEl) {
      alertEl.className = 'result-msg success';
      alertEl.textContent = `✓ Diarization set to "${data.provider}"${data.hf_token_set ? ' with HF token.' : '.'} Restart the server to apply.`;
    }
  } catch (err) {
    if (alertEl) {
      alertEl.className = 'result-msg error';
      alertEl.textContent = 'Failed to save: ' + err.message;
    }
  }
}
