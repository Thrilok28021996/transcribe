/**
 * Transcribe AI — Frontend Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  loadStats();
  loadMeetings();
  loadRecordings();
  loadSpeakers();
  loadGraph();
  initAudioDropZone();
  initLiveRecorder();
  initChat();
  initSearch();

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
      container.innerHTML = '<p class="placeholder-text">No speaker profiles registered yet.</p>';
      return;
    }

    container.innerHTML = speakers.map(s => `
      <div class="speaker-card">
        <div class="speaker-header">
          <h3>${escapeHtml(s.name)}</h3>
          <span class="status-badge">${s.has_embedding ? 'Vector Active' : 'No Vector'}</span>
        </div>
        <p>Aliases: ${s.aliases.length > 0 ? s.aliases.join(', ') : 'None'}</p>
        <p>Confidence: ${(s.confidence_avg * 100).toFixed(0)}% (${s.meeting_count} observations)</p>
      </div>
    `).join('');
  } catch (err) {
    console.error('Failed to load speakers:', err);
  }
}

// Load Knowledge Graph
async function loadGraph() {
  const container = document.getElementById('graphNodesGrid');
  if (!container) return;

  try {
    const res = await fetch('/api/graph');
    if (!res.ok) return;
    const data = await res.json();

    const metricsEl = document.getElementById('graphMetrics');
    if (metricsEl && data.stats) {
      metricsEl.textContent = `Nodes: ${data.stats.total_nodes} | Edges: ${data.stats.total_edges}`;
    }

    if (!data.nodes || data.nodes.length === 0) {
      container.innerHTML = '<p class="placeholder-text">Knowledge Graph is currently empty.</p>';
      return;
    }

    container.innerHTML = data.nodes.map(n => `
      <div class="graph-card">
        <span class="label-badge">${escapeHtml(n.label)}</span>
        <h4>${escapeHtml(n.id)}</h4>
      </div>
    `).join('');
  } catch (err) {
    console.error('Failed to load graph:', err);
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

  if (!toggleBtn) return;

  toggleBtn.addEventListener('click', async () => {
    if (!isRecording) {
      // START RECORDING (Green -> Red)
      if (errAlert) errAlert.classList.add('hidden');

      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          throw new Error('Microphone API is not supported in this browser. Please use Chrome, Edge, Safari, or Firefox.');
        }

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

      } catch (err) {
        console.error('Microphone access failed:', err);
        isRecording = false;
        recBadge.textContent = 'Microphone Error';
        recBadge.className = 'rec-badge';
        if (errAlert) {
          errAlert.textContent = `Microphone Error: ${err.message}. Please check browser permissions for http://127.0.0.1:8000.`;
          errAlert.classList.remove('hidden');
        }
      }
    } else {
      // STOP RECORDING (Red -> Processing -> Green)
      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
      }
      isRecording = false;
      toggleBtn.className = 'btn rec-toggle-btn green lg';
      toggleText.textContent = 'PROCESSING RECORDING...';
      toggleBtn.disabled = true;
    }
  });

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

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
