/**
 * Transcribe AI — Frontend Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
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

  const refreshBtn = document.getElementById('refreshRecordingsBtn');
  if (refreshBtn) refreshBtn.addEventListener('click', loadRecordings);
});


// Tab Switching
function initTabs() {
  const navBtns = document.querySelectorAll('.nav-btn');

  navBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const tabId = btn.dataset.tab;
      if (tabId) {
        window.switchTab(tabId);
      }
    });
  });
}

window.switchTab = function(tabId) {
  const navBtns = document.querySelectorAll('.nav-btn');
  const tabPanels = document.querySelectorAll('.tab-panel');

  navBtns.forEach(b => b.classList.remove('active'));
  tabPanels.forEach(p => p.classList.remove('active'));

  const targetBtn = document.querySelector(`.nav-btn[data-tab="${tabId}"]`);
  const targetPanel = document.getElementById(`tab-${tabId}`);

  if (targetBtn) targetBtn.classList.add('active');
  if (targetPanel) {
    targetPanel.classList.add('active');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
};

// Load Aggregate System Stats
async function loadStats() {
  try {
    const res = await fetch('/api/stats');
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
    const res = await fetch('/api/recordings');
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
    const res = await fetch('/api/recordings/reprocess', {
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
    const res = await fetch('/api/meetings');
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
      const res = await fetch('/api/process', {
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
      const res = await fetch('/api/ask', {
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
      const res = await fetch('/api/search', {
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
    const res = await fetch('/api/speakers');
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

        const url = editId ? `/api/speakers/${encodeURIComponent(editId)}` : '/api/speakers';
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
    const res = await fetch('/api/graph');
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
        const startRes = await fetch('/api/audio/record_start', {
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
      const res = await fetch('/api/audio/record_stop', {
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
      const res = await fetch('/api/process', {
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
    const res = await fetch('/api/audio/devices');
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

    const res = await fetch('/api/cleanup', {
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
    const res = await fetch('/api/settings');
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
    const res = await fetch('/api/settings', {
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


