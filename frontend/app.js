/**
 * PolyMind — Frontend JavaScript
 * Handles:
 *   - Form submission → POST /api/discuss
 *   - SSE connection → GET /api/stream/{session_id}
 *   - Rendering agent message cards in real time
 *   - Progress tracking, typing indicators, copy-to-clipboard
 */

const API_BASE = 'http://localhost:8000';

// Agent metadata
const AGENTS = {
  analyst:     { emoji: '🔍', label: 'Analyst',     cls: 'analyst' },
  critic:      { emoji: '⚡', label: 'Critic',      cls: 'critic' },
  expert:      { emoji: '📚', label: 'Expert',      cls: 'expert' },
  synthesizer: { emoji: '✨', label: 'Synthesizer', cls: 'synthesizer' },
  system:      { emoji: '⚙️', label: 'System',      cls: 'analyst' },
};

// State
let isRunning = false;
let lastRound = -99;
let finalContent = '';
let typingEl = null;

// ── DOM refs ────────────────────────────────────────────────────────────────
const queryInput    = document.getElementById('queryInput');
const charCount     = document.getElementById('charCount');
const roundsSelect  = document.getElementById('roundsSelect');
const submitBtn     = document.getElementById('submitBtn');
const emptyState    = document.getElementById('emptyState');
const progressWrap  = document.getElementById('progressWrap');
const progressBar   = document.getElementById('progressBar');
const statusLabel   = document.getElementById('statusLabel');
const thread        = document.getElementById('thread');
const finalWrap     = document.getElementById('finalAnswerWrap');
const finalBody     = document.getElementById('finalAnswerBody');
const copyBtn       = document.getElementById('copyBtn');

// ── Character counter ────────────────────────────────────────────────────────
queryInput.addEventListener('input', () => {
  charCount.textContent = `${queryInput.value.length} / 2000`;
});

// ── Enter key submits (Ctrl/Cmd+Enter) ─────────────────────────────────────
queryInput.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') startDiscussion();
});

// ── Main entry point ────────────────────────────────────────────────────────
async function startDiscussion() {
  const query = queryInput.value.trim();
  if (!query) {
    queryInput.focus();
    queryInput.classList.add('shake');
    setTimeout(() => queryInput.classList.remove('shake'), 500);
    return;
  }
  if (isRunning) return;

  const rounds = parseInt(roundsSelect.value, 10);

  // ── Reset UI ──
  isRunning = true;
  lastRound = -99;
  finalContent = '';
  submitBtn.disabled = true;
  submitBtn.querySelector('.submit-btn-text').textContent = 'Discussing…';

  emptyState.hidden = true;
  finalWrap.hidden = true;
  thread.innerHTML = '';
  progressWrap.hidden = false;
  statusLabel.hidden = false;
  progressBar.style.width = '0%';
  setStatus('Starting discussion…');

  // ── Calculate total messages: rounds × 3 agents + 1 synthesizer ──
  const totalMessages = rounds * 3 + 1;
  let receivedMessages = 0;

  try {
    // ── 1. Start session ──
    const resp = await fetch(`${API_BASE}/api/discuss`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, rounds }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || 'Failed to start discussion');
    }

    const session = await resp.json();
    setStatus(`Session started — ${totalMessages} responses incoming…`);

    // ── 2. Connect to SSE stream ──
    const evtSource = new EventSource(`${API_BASE}${session.stream_url}`);

    evtSource.addEventListener('agent_message', (e) => {
      const msg = JSON.parse(e.data);
      removeTypingIndicator();

      // Insert round separator when the round changes
      if (msg.round !== lastRound && msg.round !== -1) {
        if (lastRound !== -99) addRoundSeparator(msg.round);
        else if (msg.round === 0) addRoundSeparator(0);
        lastRound = msg.round;
      }

      renderAgentCard(msg);
      receivedMessages++;

      // Update progress
      const pct = Math.min((receivedMessages / totalMessages) * 90, 90);
      progressBar.style.width = `${pct}%`;

      // Show typing indicator for next agent
      const nextAgentName = getNextAgentName(msg, rounds, receivedMessages, totalMessages);
      if (nextAgentName) showTypingIndicator(nextAgentName);

      setStatus(getStatusText(msg, rounds));
      scrollThread();
    });

    evtSource.addEventListener('done', () => {
      evtSource.close();
      removeTypingIndicator();
      progressBar.style.width = '100%';
      setTimeout(() => { progressWrap.hidden = true; }, 800);
      setStatus('Discussion complete ✓');
      setTimeout(() => { statusLabel.hidden = true; }, 2000);
      resetForm();
    });

    evtSource.addEventListener('error', (e) => {
      evtSource.close();
      removeTypingIndicator();
      let errMsg = 'An error occurred during the discussion.';
      try { errMsg = JSON.parse(e.data).error; } catch {}
      renderErrorCard(errMsg);
      progressWrap.hidden = true;
      setStatus('Error — see message above');
      resetForm();
    });

    evtSource.onerror = () => {
      evtSource.close();
      removeTypingIndicator();
      renderErrorCard('Connection to server lost. Please try again.');
      progressWrap.hidden = true;
      resetForm();
    };

  } catch (err) {
    renderErrorCard(`Error: ${err.message}\n\nMake sure the backend is running:\n  cd backend\n  uvicorn main:app --reload`);
    progressWrap.hidden = true;
    setStatus('Failed to connect to backend');
    resetForm();
  }
}

// ── Render helpers ──────────────────────────────────────────────────────────

function renderAgentCard(msg) {
  const agent = AGENTS[msg.agent] || AGENTS.analyst;
  const isSynthesizer = msg.agent === 'synthesizer';

  if (isSynthesizer) {
    // Render final answer in its dedicated panel
    finalContent = msg.content;
    finalBody.textContent = msg.content;
    finalWrap.hidden = false;
    applyCodeHighlighting(finalBody);
    scrollThread();
    return;
  }

  const roundLabel = msg.round >= 0 ? `Round ${msg.round + 1}` : 'Final';

  const card = document.createElement('div');
  card.className = `agent-card agent-card--${agent.cls}`;
  card.innerHTML = `
    <div class="agent-card-header">
      <div class="agent-avatar">${agent.emoji}</div>
      <span class="agent-name">${agent.label}</span>
      <span class="agent-round-badge">${roundLabel}</span>
    </div>
    <div class="agent-card-body">
      <p></p>
    </div>
  `;

  const p = card.querySelector('p');
  p.textContent = msg.content;
  applyCodeHighlighting(p);

  thread.appendChild(card);
}

function addRoundSeparator(roundNum) {
  const sep = document.createElement('div');
  sep.className = 'round-separator';
  sep.innerHTML = `
    <div class="round-separator-line"></div>
    <span class="round-separator-label">
      ${roundNum === 0 ? 'Round 1 — Initial Perspectives' : `Round ${roundNum + 1} — Cross-Examination`}
    </span>
    <div class="round-separator-line"></div>
  `;
  thread.appendChild(sep);
}

function showTypingIndicator(agentName) {
  removeTypingIndicator();
  typingEl = document.createElement('div');
  typingEl.className = 'typing-card';
  typingEl.id = 'typingIndicator';
  typingEl.innerHTML = `
    <span class="typing-name">${agentName} is thinking</span>
    <div class="typing-dots">
      <span></span><span></span><span></span>
    </div>
  `;
  thread.appendChild(typingEl);
  scrollThread();
}

function removeTypingIndicator() {
  const existing = document.getElementById('typingIndicator');
  if (existing) existing.remove();
  typingEl = null;
}

function renderErrorCard(message) {
  const card = document.createElement('div');
  card.className = 'agent-card agent-card--critic';
  card.innerHTML = `
    <div class="agent-card-header">
      <div class="agent-avatar">⚠️</div>
      <span class="agent-name" style="color: var(--critic-color)">Error</span>
    </div>
    <div class="agent-card-body">
      <p style="font-family: var(--font-mono); font-size: 0.82rem; white-space: pre-wrap;">${escapeHtml(message)}</p>
    </div>
  `;
  thread.appendChild(card);
}

// ── Code highlighting (simple inline detection) ────────────────────────────
function applyCodeHighlighting(el) {
  // Detect markdown-style code blocks and replace with <pre><code>
  const text = el.textContent;
  if (!text.includes('```')) return;

  const html = escapeHtml(text).replace(
    /```(\w*)\n?([\s\S]*?)```/g,
    (_, lang, code) => `<pre><code class="lang-${lang || 'text'}">${code.trim()}</code></pre>`
  );

  if (html !== escapeHtml(text)) {
    el.innerHTML = html;
  }
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Status helpers ──────────────────────────────────────────────────────────
function setStatus(text) {
  statusLabel.textContent = text;
  statusLabel.hidden = false;
}

function getStatusText(msg, rounds) {
  if (msg.agent === 'synthesizer') return '✨ Synthesizer producing final answer…';
  const agentName = AGENTS[msg.agent]?.label || msg.agent_name;
  return `${agentName} responded — Round ${(msg.round ?? 0) + 1} of ${rounds}`;
}

function getNextAgentName(msg, rounds, received, total) {
  if (received >= total) return null;
  const agentSequence = ['Analyst', 'Critic', 'Expert'];
  const nextIdx = received % 3;

  // After all rounds, the next is the Synthesizer
  if (received === rounds * 3) return 'Synthesizer';
  return agentSequence[nextIdx] || null;
}

function scrollThread() {
  requestAnimationFrame(() => {
    const panel = document.querySelector('.panel-right');
    if (panel) panel.scrollTop = panel.scrollHeight;
  });
}

function resetForm() {
  isRunning = false;
  submitBtn.disabled = false;
  submitBtn.querySelector('.submit-btn-text').textContent = 'Start Discussion';
}

// ── Copy to clipboard ───────────────────────────────────────────────────────
function copyFinalAnswer() {
  navigator.clipboard.writeText(finalContent).then(() => {
    copyBtn.textContent = '✅ Copied!';
    setTimeout(() => { copyBtn.textContent = '📋 Copy Answer'; }, 2000);
  }).catch(() => {
    // Fallback
    const ta = document.createElement('textarea');
    ta.value = finalContent;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    copyBtn.textContent = '✅ Copied!';
    setTimeout(() => { copyBtn.textContent = '📋 Copy Answer'; }, 2000);
  });
}

// Expose to HTML onclick
window.startDiscussion = startDiscussion;
window.copyFinalAnswer = copyFinalAnswer;
