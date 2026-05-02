/* ═══════════════════════════════════════════════════════════════
   Collection Swarm — Core Module
   Routing, theme, mobile sidebar, toast notifications, API
   helpers, utility functions, and shared UI components.
   Loaded first; other modules depend on globals defined here.
   ═══════════════════════════════════════════════════════════════ */

const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];
const mainEl = $('#main-content');

// ── Routing ────────────────────────────────────────────────────

let currentPage = 'dashboard';
let _lastPageParams = {};

function navigateTo(page, params = {}) {
  currentPage = page;
  _lastPageParams[page] = params || {};
  $$('.nav-link').forEach(el => {
    const isActive = el.dataset.page === page;
    el.classList.toggle('active', isActive);
    if (isActive) {
      el.setAttribute('aria-current', 'page');
    } else {
      el.removeAttribute('aria-current');
    }
  });
  window.history.pushState({ page, params }, '', `#${page}`);
  closeMobileSidebar();
  renderPage(page, params);
}

window.addEventListener('popstate', (e) => {
  const state = e.state || { page: 'dashboard', params: {} };
  currentPage = state.page;
  $$('.nav-link').forEach(el => {
    const isActive = el.dataset.page === state.page;
    el.classList.toggle('active', isActive);
    if (isActive) el.setAttribute('aria-current', 'page');
    else el.removeAttribute('aria-current');
  });
  renderPage(state.page, state.params);
});

// ── Theme ──────────────────────────────────────────────────────

function toggleTheme() {
  const html = document.documentElement;
  const next = html.dataset.theme === 'dark' ? 'light' : 'dark';
  html.dataset.theme = next;
  localStorage.setItem('cs-theme', next);
  updateThemeLabel();
}

(function initTheme() {
  const saved = localStorage.getItem('cs-theme');
  if (saved) document.documentElement.dataset.theme = saved;
  updateThemeLabel();
})();

function updateThemeLabel() {
  const label = $('.theme-label');
  if (label) label.textContent = `Theme: ${fmtId(document.documentElement.dataset.theme || 'dark')}`;
}

// ── Mobile sidebar ─────────────────────────────────────────────

let _sidebarPreviousFocus = null;

function toggleMobileSidebar() {
  const sidebar = $('#sidebar');
  const overlay = $('#sidebar-overlay');
  const isOpen = sidebar.classList.toggle('open');
  if (overlay) {
    overlay.classList.toggle('open', isOpen);
    overlay.setAttribute('aria-hidden', String(!isOpen));
  }
  if (isOpen) {
    _sidebarPreviousFocus = document.activeElement;
    const firstFocusable = sidebar.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (firstFocusable) firstFocusable.focus();
  } else {
    if (_sidebarPreviousFocus) {
      _sidebarPreviousFocus.focus();
      _sidebarPreviousFocus = null;
    }
  }
}

function closeMobileSidebar() {
  const sidebar = $('#sidebar');
  const overlay = $('#sidebar-overlay');
  if (sidebar) sidebar.classList.remove('open');
  if (overlay) {
    overlay.classList.remove('open');
    overlay.setAttribute('aria-hidden', 'true');
  }
  if (_sidebarPreviousFocus) {
    _sidebarPreviousFocus.focus();
    _sidebarPreviousFocus = null;
  }
}

// ── Toast notifications ────────────────────────────────────────

const TOAST_MAX = 4;

function showToast(message, type = 'info', duration = 4000) {
  let container = $('#toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    container.setAttribute('role', 'status');
    container.setAttribute('aria-live', 'polite');
    document.body.appendChild(container);
  }

  if (type === 'error') {
    container.setAttribute('aria-live', 'assertive');
  } else {
    container.setAttribute('aria-live', 'polite');
  }

  const toasts = container.querySelectorAll('.toast:not(.toast-out)');
  if (toasts.length >= TOAST_MAX) {
    const oldest = toasts[0];
    oldest.classList.add('toast-out');
    setTimeout(() => oldest.remove(), 200);
  }

  const icons = {
    success: '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    error: '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
    info: '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
  };

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
  toast.innerHTML = `
    ${icons[type] || icons.info}
    <span class="toast-msg">${escapeHTML(message)}</span>
    <button class="toast-close" aria-label="Dismiss" onclick="this.parentElement.classList.add('toast-out');setTimeout(()=>this.parentElement.remove(),200)">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
    </button>`;
  container.appendChild(toast);

  if (duration > 0) {
    setTimeout(() => {
      if (toast.parentElement) {
        toast.classList.add('toast-out');
        setTimeout(() => toast.remove(), 200);
      }
    }, duration);
  }
}

// ── Data fetching ──────────────────────────────────────────────

async function api(path) {
  const res = await fetch(`/api${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function apiPost(path, body = {}) {
  const res = await fetch(`/api${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `API error: ${res.status}`;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

// ── Helpers ────────────────────────────────────────────────────

function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[ch]));
}
function escapeAttr(value) { return escapeHTML(value); }
function jsArg(value) { return escapeAttr(JSON.stringify(String(value ?? ''))); }
function jsArgRaw(value) { return JSON.stringify(String(value ?? '')); }
function pathPart(value) { return encodeURIComponent(String(value ?? '')); }
function safePctInput(value) {
  const n = Number(value);
  return Number.isFinite(n) ? Math.max(0, Math.min(1, n)) : 0;
}
function pct(v) { return `${Math.round(v * 100)}%`; }
function scoreClass(v) { return v >= 0.7 ? 'score-good' : v >= 0.4 ? 'score-mid' : 'score-bad'; }
function fmtId(id) { return String(id ?? '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }
function fmtMoney(v) { return `$${(Number(v) || 0).toFixed(4)}`; }
function fmtNum(v) { return Number(v).toLocaleString(); }
function pctSafe(v) { return pct(safePctInput(v)); }
function scoreClassSafe(v) { return scoreClass(safePctInput(v)); }
function relTime(iso) {
  if (!iso) return '\u2014';
  const d = new Date(iso);
  const now = new Date();
  const diff = now - d;
  if (diff < 60000) return 'just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function skeleton() {
  return `<div class="skeleton" aria-label="Loading content">
    <div class="skeleton-row">
      <div class="skeleton-block"></div>
      <div class="skeleton-block"></div>
      <div class="skeleton-block"></div>
    </div>
    <div class="skeleton-line"></div>
    <div class="skeleton-line"></div>
    <div class="skeleton-line"></div>
    <div class="skeleton-line"></div>
    <div class="skeleton-line"></div>
  </div>`;
}

function emptyState(title, msg) {
  return `
    <div class="empty-state" role="status">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
      <h3>${escapeHTML(title)}</h3>
      <p>${escapeHTML(msg)}</p>
    </div>`;
}

function scoreBarHTML(label, value) {
  value = safePctInput(value);
  const isRisk = label.toLowerCase().includes('escalation');
  const interpreted = isRisk ? 1 - value : value;
  const cls = scoreClass(interpreted);
  const colorVar = cls === 'score-good' ? '--success' : cls === 'score-mid' ? '--warning' : '--danger';
  const safeLabel = escapeHTML(label);
  const definitions = {
    'Payment Probability': 'Estimated likelihood that the debtor would pay based on judge assessment. Higher is better.',
    'Compliance Score': 'How closely the conversation stays within collection policy and constraints. Higher is better.',
    'Debtor Satisfaction': 'Estimated debtor trust and comfort after the conversation. Higher is better.',
    'Rapport Built': 'How well the collector established trust and cooperation. Higher is better.',
    'Escalation Risk': 'Likelihood that the interaction increases complaints, disputes, or hostility. Lower is better.',
    'Efficiency': 'How quickly the conversation reached a useful endpoint. Higher is better.',
  };
  const definition = definitions[label] || `${label} score.`;
  const meaning = cls === 'score-good' ? 'Good' : cls === 'score-mid' ? 'Watch' : 'Risk';
  const labelText = isRisk ? `${label} (lower is better)` : label;
  return `
    <div class="judgment-score-item">
      <span class="judgment-score-label" title="${escapeAttr(definition)}">${escapeHTML(labelText)}</span>
      <div class="score-bar-wrap">
        <div class="score-bar" role="meter" aria-valuenow="${Math.round(value * 100)}" aria-valuemin="0" aria-valuemax="100" aria-label="${escapeAttr(`${labelText}: ${definition}`)}">
          <div class="score-bar-fill" style="width:${value * 100}%;background:var(${colorVar})"></div>
        </div>
        <span class="score-bar-label ${cls}"><span aria-hidden="true">${cls === 'score-good' ? 'OK' : cls === 'score-mid' ? '!' : 'X'}</span> ${pct(value)} ${meaning}</span>
      </div>
    </div>`;
}

function outcomeBadge(outcome) {
  const map = {
    'full_payment': 'badge-success',
    'partial_payment': 'badge-success',
    'payment_plan': 'badge-info',
    'promise_to_pay': 'badge-info',
    'no_commitment': 'badge-warning',
    'refusal': 'badge-danger',
    'hang_up': 'badge-danger',
  };
  return `<span class="badge ${map[outcome] || 'badge-neutral'}">${escapeHTML(fmtId(outcome))}</span>`;
}

function statusBadge(status) {
  const map = {
    completed: 'badge-success',
    failed: 'badge-danger',
    running: 'badge-info',
    queued: 'badge-warning',
    waiting_for_human: 'badge-warning',
    ai_thinking: 'badge-info',
    judging: 'badge-info',
  };
  return `<span class="badge ${map[status] || 'badge-neutral'}">${escapeHTML(fmtId(status))}</span>`;
}

function chatHTML(transcript = []) {
  const MAX_STAGGER = 10;
  return transcript.map((m, i) => {
    const avatarMap = { collector: 'C', debtor: 'D', system: 'S', judge: 'J' };
    const role = avatarMap[m.role] ? m.role : 'system';
    const delay = Math.min(i, MAX_STAGGER) * 40;
    return `
      <div class="chat-msg ${role}" style="animation-delay:${delay}ms" role="listitem">
        <div class="chat-avatar" aria-hidden="true">${avatarMap[role] || '?'}</div>
        <div class="chat-bubble">
          <div class="chat-role">${escapeHTML(m.role)}</div>
          ${escapeHTML(m.content || '')}
        </div>
      </div>`;
  }).join('');
}

function progressHTML(completed, failed, total) {
  completed = Number(completed) || 0;
  failed = Number(failed) || 0;
  total = Number(total) || 0;
  const done = completed + failed;
  const pctDone = total ? Math.round((done / total) * 100) : 0;
  return `
    <div class="progress-wrap" role="progressbar" aria-valuenow="${pctDone}" aria-valuemin="0" aria-valuemax="100">
      <div class="progress-bar-fill" style="width:${pctDone}%"></div>
    </div>
    <div class="progress-meta">${done} of ${total} finished \u00b7 ${completed} completed \u00b7 ${failed} failed</div>`;
}

function runSelectOptions(items, selectedId) {
  return items.map(item => `<option value="${escapeAttr(item.id)}" ${item.id === selectedId ? 'selected' : ''}>${escapeHTML(fmtId(item.id))}</option>`).join('');
}

function modelSelectOptions(items, selectedId) {
  return items.map(item => `<option value="${escapeAttr(item.id)}" ${item.id === selectedId ? 'selected' : ''}>${escapeHTML(item.id)}</option>`).join('');
}

function profileSummary(profile) {
  if (!profile) return 'Select a profile to see debtor context.';
  const constraints = (profile.constraints || []).slice(0, 2).map(c => c.text).join(' ');
  return `${fmtId(profile.archetype)} debtor, $${Number(profile.debt_amount || 0).toLocaleString()} ${profile.debt_type || 'debt'}. ${constraints || profile.backstory || ''}`.trim();
}

function strategySummary(strategy) {
  if (!strategy) return 'Select a strategy to see its approach.';
  return `${fmtId(strategy.tone)} tone, ${fmtId(strategy.opening_approach)} opening, ${fmtId(strategy.negotiation_tactic)} negotiation.`;
}

function updateSelectSummary(selectId, summaryId, items, formatter) {
  const select = $(`#${selectId}`);
  const summary = $(`#${summaryId}`);
  if (!select || !summary) return;
  const item = items.find(entry => entry.id === select.value);
  summary.textContent = formatter(item);
}

function advancedModelSettings(prefix, conversationOpts, judgeOpts, conversationLabel = 'Conversation model') {
  return `
    <details class="advanced-settings">
      <summary>Advanced model settings</summary>
      <div class="advanced-settings-body">
        ${selectField(`${prefix}-conversation-model`, conversationLabel, conversationOpts)}
        ${selectField(`${prefix}-judge-model`, 'Judge model', judgeOpts)}
      </div>
    </details>`;
}

function modelLabel(model) {
  if (!model) return '';
  return `${model.id}${model.provider ? ` (${model.provider})` : ''}`;
}

function modelShortLabel(id) {
  return String(id || '').replace(/^cursor-/, '').replace(/^nim-/, '');
}

function linkButton(label, onclick, extraClass = '') {
  return `<button class="btn ${extraClass}" type="button" onclick="${escapeAttr(onclick)}">${escapeHTML(label)}</button>`;
}

function checkedBoxes(items, name) {
  return items.map(item => `
    <label class="check-row">
      <input type="checkbox" name="${escapeAttr(name)}" value="${escapeAttr(item.id)}" checked>
      <span>${escapeHTML(fmtId(item.id))}</span>
    </label>`).join('');
}

function selectedValues(name) {
  return $$(`input[name="${name}"]:checked`).map(input => input.value);
}

const OUTCOME_COLORS = {
  'full_payment': 'var(--chart-7)',
  'partial_payment': 'var(--chart-1)',
  'payment_plan': 'var(--chart-2)',
  'promise_to_pay': 'var(--chart-3)',
  'no_commitment': 'var(--chart-6)',
  'refusal': 'var(--chart-5)',
  'hang_up': 'var(--chart-4)',
};

const METRIC_DEFINITIONS = {
  'Payment Probability': 'Estimated likelihood that the debtor would pay based on judge assessment. Higher is better.',
  'Compliance Score': 'How closely the conversation stayed within compliance expectations. Higher is better.',
  'Debtor Satisfaction': 'Estimated debtor sentiment and perceived fairness. Higher is better.',
  'Rapport Built': 'How much trust and collaboration the conversation created. Higher is better.',
  'Escalation Risk': 'Risk that the interaction increases complaints, avoidance, or regulatory exposure. Lower is better.',
  'Efficiency': 'Conversation progress relative to the expected turn budget. Higher means fewer wasted turns.',
  Runs: 'Total simulations recorded in the current database.',
  Completed: 'Simulations that finished and produced a saved result.',
  Failed: 'Simulations that ended with an error.',
  Success: 'Completed runs divided by all recorded runs.',
};

function metricLabelHTML(label, extra = '') {
  const title = METRIC_DEFINITIONS[label] || '';
  return `<span class="metric-help" title="${escapeAttr(title)}">${escapeHTML(label)}${extra ? ` <span class="metric-note">${escapeHTML(extra)}</span>` : ''}</span>`;
}

function performanceSummaryHTML(performance) {
  if (!performance || !performance.run_count) return '';
  return `
    <div class="performance-summary" aria-label="Performance summary">
      <span><strong>${fmtNum(performance.run_count)}</strong> runs</span>
      <span><strong>${pct(performance.payment_probability)}</strong> payment</span>
      <span><strong>${pct(performance.compliance_score)}</strong> compliance</span>
    </div>`;
}

