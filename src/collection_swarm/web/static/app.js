/* ═══════════════════════════════════════════════════════════════
   Collection Swarm — Single-Page Application
   Production edition: page transitions, toast notifications,
   keyboard navigation, filter state management, loading states,
   mobile sidebar toggle, scroll-to-top on navigate.
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

// ══════════════════════════════════════════════════════════════
//  PAGE RENDERERS
// ══════════════════════════════════════════════════════════════

async function renderPage(page, params = {}) {
  mainEl.innerHTML = skeleton();
  mainEl.scrollTop = 0;
  try {
    switch (page) {
      case 'dashboard': await renderDashboard(params); break;
      case 'runs': await renderRuns(); break;
      case 'launch': await renderLaunch(params); break;
      case 'matrix': await renderMatrix(params); break;
      case 'manual': await renderManual(params); break;
      case 'playbook': await renderPlaybook(); break;
      case 'compliance': await renderCompliance(); break;
      case 'profiles': await renderProfiles(); break;
      case 'strategies': await renderStrategies(); break;
      default: mainEl.innerHTML = emptyState('Not Found', 'Page not found.');
    }
    mainEl.classList.remove('page-enter');
    void mainEl.offsetWidth;
    mainEl.classList.add('page-enter');
  } catch (err) {
    mainEl.innerHTML = emptyState('Error', err.message);
  }
}

// ── Dashboard ──────────────────────────────────────────────────

async function renderDashboard() {
  const [data, compliance] = await Promise.all([
    api('/dashboard'),
    api('/compliance/exclusions'),
  ]);
  const { total_runs, completed, failed, average_scores: avg, outcome_distribution: dist, cost } = data;

  const totalOutcomes = Object.values(dist).reduce((a, b) => a + b, 0) || 1;
  const outcomeRows = Object.entries(dist).sort((a, b) => b[1] - a[1]).map(([outcome, count]) => {
    const w = (count / totalOutcomes) * 100;
    const color = OUTCOME_COLORS[outcome] || 'var(--chart-1)';
    return `
      <div class="dist-row">
        <span class="dist-label">${escapeHTML(fmtId(outcome))}</span>
        <div class="dist-bar-track">
          <div class="dist-bar-fill" style="width:${Math.max(w, 6)}%;background:${color}"><span>${pct(count / totalOutcomes)}</span></div>
        </div>
        <span class="dist-count">${count}</span>
      </div>`;
  }).join('');

  const tabs = data.profiles.map((p, i) => {
    const tabId = `profile-tab-${i}`;
    const panelId = 'strategy-comparison';
    return `<button id="${tabId}" class="tab-btn${i === 0 ? ' active' : ''}" onclick="switchProfileTab(${jsArg(p)}, this)" onkeydown="handleProfileTabKey(event)" role="tab" aria-selected="${i === 0}" aria-controls="${panelId}" tabindex="${i === 0 ? '0' : '-1'}">${escapeHTML(fmtId(p))}</button>`;
  }).join('');
  const strategySection = data.profiles.length ? `
    <section class="card decision-card">
      <div class="card-header">
        <div>
          <h2>Strategy Rankings</h2>
          <p class="section-lead">Best strategy per debtor profile, ranked by payment probability.</p>
        </div>
      </div>
      <div class="card-body">
        <div class="tabs" role="tablist" aria-label="Profile strategy rankings" id="profile-tabs">${tabs}</div>
        <div id="strategy-comparison" role="tabpanel" tabindex="0" aria-labelledby="profile-tab-0">${skeleton()}</div>
      </div>
    </section>` : '';

  const complianceBanner = renderComplianceBanner(compliance);
  const successRate = total_runs > 0 ? Math.round((completed / total_runs) * 100) : 0;

  mainEl.innerHTML = `
    <div class="page-header">
      <h1>Dashboard</h1>
      <p>Which strategy to use, which to avoid, and why.</p>
    </div>

    <div class="overview-strip" role="status" aria-label="Simulation summary">
      <div class="overview-item">
        <span class="overview-label">${metricLabelHTML('Runs')}</span>
        <span class="overview-value">${fmtNum(total_runs)}</span>
      </div>
      <div class="overview-sep" aria-hidden="true"></div>
      <div class="overview-item">
        <span class="overview-label">${metricLabelHTML('Completed')}</span>
        <span class="overview-value">${fmtNum(completed)}</span>
      </div>
      <div class="overview-sep" aria-hidden="true"></div>
      <div class="overview-item">
        <span class="overview-label">${metricLabelHTML('Failed')}</span>
        <span class="overview-value">${fmtNum(failed)}</span>
      </div>
      <div class="overview-sep" aria-hidden="true"></div>
      <div class="overview-item">
        <span class="overview-label">${metricLabelHTML('Success')}</span>
        <span class="overview-value">${successRate}%</span>
      </div>
    </div>

    ${total_runs === 0 ? renderFirstRunPanel() : ''}
    ${strategySection}
    ${complianceBanner}

    <div class="grid-2">
      <div class="card">
        <div class="card-header"><h2>Average Scores</h2></div>
        <div class="card-body">
          ${total_runs === 0 ? emptyState('No Data', 'Run simulations to see scores.') : `
          ${scoreBarHTML('Payment Probability', avg.payment_probability)}
          ${scoreBarHTML('Compliance Score', avg.compliance_score)}
          ${scoreBarHTML('Debtor Satisfaction', avg.debtor_satisfaction)}
          ${scoreBarHTML('Rapport Built', avg.rapport_built)}
          ${scoreBarHTML('Escalation Risk', avg.escalation_risk)}
          `}
        </div>
      </div>

      <div class="card">
        <div class="card-header"><h2>Outcome Distribution</h2></div>
        <div class="card-body">
          ${total_runs === 0 ? emptyState('No Data', 'Run simulations to see outcomes.') : `
          <div class="dist-bars" role="img" aria-label="Outcome distribution chart">${outcomeRows}</div>
          `}
        </div>
      </div>
    </div>

    <details class="operational-details">
      <summary>Operational Details</summary>
      <div class="operational-grid">
        <span>Estimated cost <strong>${fmtMoney(cost.estimated_cost_usd || 0)}</strong></span>
        <span>Input tokens <strong>${fmtNum(cost.input_tokens || 0)}</strong></span>
        <span>Output tokens <strong>${fmtNum(cost.output_tokens || 0)}</strong></span>
      </div>
    </details>
  `;

  if (data.profiles.length) setTimeout(() => loadStrategyComparison(data.profiles[0]), 0);
}

function renderFirstRunPanel() {
  return `
    <section class="first-run-panel" aria-label="Getting started">
      <div>
        <p class="eyebrow">Start here</p>
        <h2>Run enough evidence to choose a collection strategy.</h2>
      </div>
      <div class="first-run-actions">
        <button class="first-run-action" type="button" onclick="navigateTo('launch', { demo: true })"><strong>Run a demo simulation</strong><span>Use defaults to create the first judged transcript.</span></button>
        <button class="first-run-action" type="button" onclick="navigateTo('matrix', { profile: 'cooperative_hardship' })"><strong>Compare strategies for a profile</strong><span>Run every strategy against one debtor archetype.</span></button>
        <button class="first-run-action" type="button" onclick="navigateTo('compliance')"><strong>Review compliance risks</strong><span>Check what thresholds will exclude a strategy.</span></button>
      </div>
    </section>`;
}

function renderComplianceBanner(data) {
  const exclusions = data.exclusions || [];
  if (!exclusions.length) {
    return `<div class="compliance-strip success"><strong>No compliance exceptions</strong><span>${fmtNum(data.total_completed_runs || 0)} completed runs checked.</span><button class="text-link" type="button" onclick="navigateTo('compliance')">View details</button></div>`;
  }
  const critical = exclusions.slice(0, 3).map(e =>
    `<span>${escapeHTML(fmtId(e.strategy_id))} x ${escapeHTML(fmtId(e.profile_id))}: ${pct(e.compliance_score)} compliance, ${pct(e.escalation_risk)} escalation</span>`
  ).join('');
  return `<div class="compliance-strip danger"><strong>${exclusions.length} compliance exception${exclusions.length !== 1 ? 's' : ''}</strong><span class="compliance-strip-items">${critical}</span><button class="text-link" type="button" onclick="navigateTo('compliance')">View details</button></div>`;
}

window.switchProfileTab = async function(profileId, btn) {
  $$('#profile-tabs .tab-btn').forEach(b => {
    const selected = b === btn;
    b.classList.toggle('active', selected);
    b.setAttribute('aria-selected', String(selected));
    b.setAttribute('tabindex', selected ? '0' : '-1');
  });
  const panel = $('#strategy-comparison');
  if (panel) panel.setAttribute('aria-labelledby', btn.id);
  btn.focus();
  await loadStrategyComparison(profileId);
};

window.handleProfileTabKey = function(event) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
  event.preventDefault();
  const tabs = $$('#profile-tabs .tab-btn');
  const index = tabs.indexOf(event.currentTarget);
  let next = index;
  if (event.key === 'ArrowLeft') next = index <= 0 ? tabs.length - 1 : index - 1;
  if (event.key === 'ArrowRight') next = index >= tabs.length - 1 ? 0 : index + 1;
  if (event.key === 'Home') next = 0;
  if (event.key === 'End') next = tabs.length - 1;
  tabs[next].click();
};

async function loadStrategyComparison(profileId) {
  const container = $('#strategy-comparison');
  if (!container) return;
  container.innerHTML = skeleton();
  try {
    const data = await api(`/profiles/${pathPart(profileId)}/strategies`);
    if (!data.strategies.length) {
      container.innerHTML = emptyState('No Data', `No completed simulations for ${fmtId(profileId)}.`);
      return;
    }
    container.innerHTML = data.strategies.map((s, i) => {
      const escalationClass = scoreClass(1 - safePctInput(s.mean_escalation_risk));
      return `
      <div class="comparison-row">
        <div class="comparison-rank" aria-label="Rank ${i + 1}">${i + 1}</div>
        <div class="comparison-name">${escapeHTML(fmtId(s.strategy_id))}</div>
        <div class="comparison-scores">
          <div class="comparison-metric">
            <span class="comparison-metric-value ${scoreClass(s.mean_payment_probability)}">${pct(s.mean_payment_probability)}</span>
            <span class="comparison-metric-label">Payment</span>
          </div>
          <div class="comparison-metric">
            <span class="comparison-metric-value ${scoreClass(s.mean_compliance_score)}">${pct(s.mean_compliance_score)}</span>
            <span class="comparison-metric-label">Compliance</span>
          </div>
          <div class="comparison-metric">
            <span class="comparison-metric-value ${escalationClass}">${pct(s.mean_escalation_risk)}</span>
            <span class="comparison-metric-label">Escalation, lower is better</span>
          </div>
          <div class="comparison-metric">
            <span class="comparison-metric-value">${s.simulation_count}</span>
            <span class="comparison-metric-label">Runs</span>
          </div>
        </div>
      </div>`;
    }).join('');
  } catch (err) {
    container.innerHTML = emptyState('Error', err.message);
  }
}

// ── Runs ───────────────────────────────────────────────────────

async function renderRuns() {
  const [runs, dashboard] = await Promise.all([
    api('/runs?status='),
    api('/dashboard'),
  ]);

  const profiles = dashboard.profiles || [];
  const strategies = dashboard.strategies || [];

  const profileOpts = profiles.map(p => `<option value="${escapeAttr(p)}">${escapeHTML(fmtId(p))}</option>`).join('');
  const strategyOpts = strategies.map(s => `<option value="${escapeAttr(s)}">${escapeHTML(fmtId(s))}</option>`).join('');

  mainEl.innerHTML = `
    <div class="page-header page-header-actions">
      <div>
        <h1>Simulation Runs</h1>
        <p>${runs.length} simulation${runs.length !== 1 ? 's' : ''} recorded</p>
      </div>
      <button class="btn" type="button" onclick="exportRunsCSV()">Export CSV</button>
    </div>

    <div class="filter-bar" role="search" aria-label="Filter simulations">
      <label class="sr-only" for="filter-search">Search runs</label>
      <input class="form-input filter-search" id="filter-search" type="search" placeholder="Search runs, profiles, strategies, outcomes, transcripts" oninput="debouncedFilterRuns()" aria-label="Search runs">
      <label class="sr-only" for="filter-status">Status</label>
      <select class="filter-select" id="filter-status" onchange="filterRuns()" aria-label="Filter by status">
        <option value="">All Status</option>
        <option value="completed">Completed</option>
        <option value="failed">Failed</option>
      </select>
      <label class="sr-only" for="filter-profile">Profile</label>
      <select class="filter-select" id="filter-profile" onchange="filterRuns()" aria-label="Filter by profile">
        <option value="">All Profiles</option>
        ${profileOpts}
      </select>
      <label class="sr-only" for="filter-strategy">Strategy</label>
      <select class="filter-select" id="filter-strategy" onchange="filterRuns()" aria-label="Filter by strategy">
        <option value="">All Strategies</option>
        ${strategyOpts}
      </select>
      <button class="filter-clear" id="filter-clear-btn" onclick="clearFilters()" style="display:none" aria-label="Clear all filters">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        Clear filters
      </button>
      <span class="filter-count" id="filter-count"></span>
    </div>
    <div class="filter-chips" id="filter-chips" aria-live="polite"></div>

    <div class="card">
      <div class="card-body no-padding">
        <div style="overflow-x:auto;max-height:calc(100vh - 320px)">
          <table class="data-table" id="runs-table" aria-label="Simulation runs">
            <thead><tr id="runs-head-row"></tr></thead>
            <tbody id="runs-tbody"></tbody>
          </table>
        </div>
      </div>
    </div>
  `;

  window._allRuns = runs;
  window._sortColumn = window._sortColumn || 'started_at';
  window._sortDirection = window._sortDirection || 'desc';
  renderRunHeaders();
  filterRuns();
}

window.filterRuns = function() {
  const status = ($('#filter-status') || {}).value || '';
  const profile = ($('#filter-profile') || {}).value || '';
  const strategy = ($('#filter-strategy') || {}).value || '';
  const search = (($('#filter-search') || {}).value || '').trim().toLowerCase();

  let filtered = window._allRuns || [];
  if (status) filtered = filtered.filter(r => r.status === status);
  if (profile) filtered = filtered.filter(r => r.profile_id === profile);
  if (strategy) filtered = filtered.filter(r => r.strategy_id === strategy);
  if (search) {
    filtered = filtered.filter(r => {
      const j = r.judgment || {};
      const haystack = [
        r.id,
        r.profile_id,
        r.strategy_id,
        r.status,
        j.payment_outcome,
        r.conversation_model,
        r.judge_model,
        r.error_message,
      ].join(' ').toLowerCase();
      return haystack.includes(search);
    });
  }
  filtered = sortRuns(filtered);
  window._filteredRuns = filtered;

  const hasFilters = status || profile || strategy || search;
  const clearBtn = $('#filter-clear-btn');
  if (clearBtn) clearBtn.style.display = hasFilters ? '' : 'none';

  $$('.filter-select').forEach(el => {
    el.classList.toggle('has-value', !!el.value);
  });

  const countEl = $('#filter-count');
  if (countEl) {
    const total = (window._allRuns || []).length;
    countEl.textContent = hasFilters ? `${filtered.length} of ${total}` : `${total} total`;
  }
  const chipsEl = $('#filter-chips');
  if (chipsEl) chipsEl.innerHTML = renderFilterChips({ status, profile, strategy, search });

  const tbody = $('#runs-tbody');
  if (!tbody) return;

  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="10">${emptyState('No Runs', 'No simulations match the current filters.')}</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(r => {
    const j = r.judgment;
    return `
      <tr onclick="openTranscript(${jsArg(r.id)})" tabindex="0" role="button" aria-label="View transcript for ${escapeAttr(r.id)}" onkeydown="handleRunRowKey(event, ${jsArg(r.id)})">
        <td>${escapeHTML(r.id)}</td>
        <td>${statusBadge(r.status)}</td>
        <td>${escapeHTML(fmtId(r.profile_id))}</td>
        <td>${escapeHTML(fmtId(r.strategy_id))}</td>
        <td>${j ? outcomeBadge(j.payment_outcome) : '\u2014'}</td>
        <td class="${j ? scoreClass(j.payment_probability) : ''}">${j ? pct(j.payment_probability) : '\u2014'}</td>
        <td class="${j ? scoreClass(j.compliance_score) : ''}">${j ? pct(j.compliance_score) : '\u2014'}</td>
        <td>${r.turn_count}</td>
        <td>${r.ended_by ? escapeHTML(fmtId(r.ended_by)) : '\u2014'}</td>
        <td title="${escapeAttr(r.started_at || '')}">${relTime(r.started_at)}</td>
      </tr>`;
  }).join('');
};

let _runFilterTimer = null;
window.debouncedFilterRuns = function() {
  clearTimeout(_runFilterTimer);
  _runFilterTimer = setTimeout(filterRuns, 200);
};

window.handleRunRowKey = function(event, runId) {
  if (event.key !== 'Enter' && event.key !== ' ') return;
  event.preventDefault();
  openTranscript(runId);
};

window.clearFilters = function() {
  $$('.filter-select').forEach(el => { el.value = ''; });
  const search = $('#filter-search');
  if (search) search.value = '';
  filterRuns();
};

function renderFilterChips(filters) {
  const chips = [];
  if (filters.status) chips.push(['status', `Status: ${fmtId(filters.status)}`]);
  if (filters.profile) chips.push(['profile', `Profile: ${fmtId(filters.profile)}`]);
  if (filters.strategy) chips.push(['strategy', `Strategy: ${fmtId(filters.strategy)}`]);
  if (filters.search) chips.push(['search', `Search: ${filters.search}`]);
  return chips.map(([key, label]) => `
    <span class="filter-chip">
      ${escapeHTML(label)}
      <button type="button" onclick="clearFilter(${jsArg(key)})" aria-label="Clear ${escapeAttr(label)}">x</button>
    </span>
  `).join('');
}

window.clearFilter = function(key) {
  const map = {
    status: '#filter-status',
    profile: '#filter-profile',
    strategy: '#filter-strategy',
    search: '#filter-search',
  };
  const el = $(map[key]);
  if (el) el.value = '';
  filterRuns();
};

function sortRuns(runs) {
  const column = window._sortColumn || 'started_at';
  const direction = window._sortDirection === 'asc' ? 1 : -1;
  return runs.slice().sort((a, b) => {
    const av = sortValue(a, column);
    const bv = sortValue(b, column);
    if (av < bv) return -1 * direction;
    if (av > bv) return 1 * direction;
    return 0;
  });
}

function sortValue(run, column) {
  const judgment = run.judgment || {};
  const values = {
    id: run.id,
    status: run.status,
    profile_id: fmtId(run.profile_id),
    strategy_id: fmtId(run.strategy_id),
    payment_outcome: judgment.payment_outcome || '',
    payment_probability: Number(judgment.payment_probability || 0),
    compliance_score: Number(judgment.compliance_score || 0),
    turn_count: Number(run.turn_count || 0),
    ended_by: run.ended_by || '',
    started_at: run.started_at || '',
  };
  return values[column] ?? '';
}

function sortableHeader(label, column) {
  const active = window._sortColumn === column;
  const arrow = active ? (window._sortDirection === 'asc' ? 'up' : 'down') : '';
  return `<button class="sort-btn${active ? ' active' : ''}" type="button" onclick="setRunSort(${jsArg(column)})">${escapeHTML(label)} <span aria-hidden="true">${arrow === 'up' ? '^' : arrow === 'down' ? 'v' : ''}</span></button>`;
}

window.setRunSort = function(column) {
  if (window._sortColumn === column) {
    window._sortDirection = window._sortDirection === 'asc' ? 'desc' : 'asc';
  } else {
    window._sortColumn = column;
    window._sortDirection = column === 'started_at' ? 'desc' : 'asc';
  }
  renderRunHeaders();
  filterRuns();
};

function renderRunHeaders() {
  const row = $('#runs-head-row');
  if (!row) return;
  row.innerHTML = [
    ['ID', 'id'],
    ['Status', 'status'],
    ['Profile', 'profile_id'],
    ['Strategy', 'strategy_id'],
    ['Outcome', 'payment_outcome'],
    ['Payment', 'payment_probability'],
    ['Compliance', 'compliance_score'],
    ['Turns', 'turn_count'],
    ['Ended By', 'ended_by'],
    ['Time', 'started_at'],
  ].map(([label, column]) => `<th scope="col">${sortableHeader(label, column)}</th>`).join('');
}

function exportRunsCSV() {
  const rows = window._filteredRuns || [];
  const headers = ['id', 'status', 'profile_id', 'strategy_id', 'outcome', 'payment_probability', 'compliance_score', 'debtor_satisfaction', 'escalation_risk', 'turn_count', 'ended_by', 'started_at'];
  const csvRows = [headers.join(',')].concat(rows.map(run => {
    const j = run.judgment || {};
    return [
      run.id,
      run.status,
      run.profile_id,
      run.strategy_id,
      j.payment_outcome || '',
      j.payment_probability ?? '',
      j.compliance_score ?? '',
      j.debtor_satisfaction ?? '',
      j.escalation_risk ?? '',
      run.turn_count ?? '',
      run.ended_by || '',
      run.started_at || '',
    ].map(csvCell).join(',');
  }));
  const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `collection-swarm-runs-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function csvCell(value) {
  return `"${String(value ?? '').replace(/"/g, '""')}"`;
}

window.updateLaunchDescriptions = function() {
  const options = window._runOptions || { profiles: [], strategies: [] };
  updateSelectSummary('launch-profile', 'launch-profile-summary', options.profiles, profileSummary);
  updateSelectSummary('launch-strategy', 'launch-strategy-summary', options.strategies, strategySummary);
};

// ── Launch single run ───────────────────────────────────────────

async function renderLaunch(params = {}) {
  const options = await api('/config/run-options');
  const selectedProfile = params.profile || (params.demo ? 'cooperative_hardship' : '');
  const selectedStrategy = params.strategy || (params.demo ? 'empathetic_payment_plan' : '');
  const profileOpts = runSelectOptions(options.profiles, selectedProfile);
  const strategyOpts = runSelectOptions(options.strategies, selectedStrategy);
  const conversationOpts = modelSelectOptions(options.conversation_models, options.defaults.conversation_model);
  const judgeOpts = modelSelectOptions(options.judge_models, options.defaults.judge_model);

  window._runOptions = options;
  mainEl.innerHTML = `
    <div class="page-header">
      <h1>Launch Run</h1>
      <p>Choose the debtor and strategy; defaults handle the model setup.</p>
    </div>
    <div class="grid-2">
      <div class="card">
        <div class="card-header"><h2>Configuration</h2></div>
        <div class="card-body">
          <form class="control-form" onsubmit="startSingleRun(event)">
            ${selectField('launch-profile', 'Profile', profileOpts, "updateLaunchDescriptions()")}
            <p class="field-summary" id="launch-profile-summary"></p>
            ${selectField('launch-strategy', 'Strategy', strategyOpts, "updateLaunchDescriptions()")}
            <p class="field-summary" id="launch-strategy-summary"></p>
            ${advancedModelSettings('launch', conversationOpts, judgeOpts)}
            <button class="btn btn-primary" type="submit" id="launch-btn">Start simulation</button>
          </form>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><h2>Live Progress</h2><div id="single-job-status">${statusBadge('queued')}</div></div>
        <div class="card-body" id="single-job-panel">
          ${emptyState('Ready', 'Configure and start a simulation to see live progress here.')}
        </div>
      </div>
    </div>`;
  updateLaunchDescriptions();
}

window.startSingleRun = async function(event) {
  event.preventDefault();
  clearPoll('single');
  const panel = $('#single-job-panel');
  const status = $('#single-job-status');
  const btn = $('#launch-btn');
  panel.innerHTML = skeleton();
  if (btn) { btn.classList.add('btn-loading'); btn.disabled = true; }
  try {
    const job = await apiPost('/jobs/simulations', {
      profile_id: $('#launch-profile').value,
      strategy_id: $('#launch-strategy').value,
      conversation_model: $('#launch-conversation-model').value,
      judge_model: $('#launch-judge-model').value,
    });
    status.innerHTML = statusBadge(job.status);
    renderJobPanel(job, panel);
    showToast('Simulation started', 'success');
    window._pollers.single = setInterval(() => pollJob(job.id, 'single-job-panel', 'single-job-status', 'single'), 800);
  } catch (err) {
    panel.innerHTML = emptyState('Launch failed', err.message);
    showToast(err.message, 'error');
  } finally {
    if (btn) { btn.classList.remove('btn-loading'); btn.disabled = false; }
  }
};

// ── Matrix runs ─────────────────────────────────────────────────

async function renderMatrix(params = {}) {
  const [options, jobs] = await Promise.all([api('/config/run-options'), api('/jobs')]);
  const profiles = checkboxList('matrix-profiles', options.profiles.map(p => [p.id, fmtId(p.id)]), params.profile ? [params.profile] : null);
  const strategies = checkboxList('matrix-strategies', options.strategies.map(s => [s.id, fmtId(s.id)]));
  const conversationOpts = modelSelectOptions(options.conversation_models, options.defaults.conversation_model);
  const judgeOpts = modelSelectOptions(options.judge_models, options.defaults.judge_model);

  window._runOptions = options;
  mainEl.innerHTML = `
    <div class="page-header">
      <h1>Batch Comparison</h1>
      <p>Compare strategy performance across selected debtor profiles.</p>
    </div>
    <div class="grid-2">
      <div class="card">
        <div class="card-header"><h2>Matrix Setup</h2></div>
        <div class="card-body">
          <form class="control-form" onsubmit="startMatrixRun(event)">
            <div class="form-field"><label>Profiles</label><div class="checkbox-grid" onchange="updateMatrixCount()">${profiles}</div></div>
            <div class="form-field"><label>Strategies</label><div class="checkbox-grid" onchange="updateMatrixCount()">${strategies}</div></div>
            ${advancedModelSettings('matrix', conversationOpts, judgeOpts)}
            <div class="btn-row">
              ${inputField('matrix-reps', 'Reps', options.defaults.reps || 1, 1, 100, "updateMatrixCount()")}
              ${inputField('matrix-concurrency', 'Concurrency', 2, 1, 10)}
            </div>
            <div class="matrix-count" id="matrix-count" aria-live="polite"></div>
            <button class="btn btn-primary" type="submit" id="matrix-btn">Start matrix</button>
          </form>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><h2>Progress</h2><div id="matrix-job-status">${statusBadge('queued')}</div></div>
        <div class="card-body" id="matrix-job-panel">
          ${jobs.length ? jobs.map(jobSummaryHTML).join('') : emptyState('No Jobs', 'Start a matrix run to watch progress.')}
        </div>
      </div>
    </div>`;
  updateMatrixCount();
}

window.startMatrixRun = async function(event) {
  event.preventDefault();
  clearPoll('matrix');
  const panel = $('#matrix-job-panel');
  const status = $('#matrix-job-status');
  const btn = $('#matrix-btn');
  panel.innerHTML = skeleton();
  if (btn) { btn.classList.add('btn-loading'); btn.disabled = true; }
  try {
    const job = await apiPost('/jobs/matrix', {
      profile_ids: checkedValues('matrix-profiles'),
      strategy_ids: checkedValues('matrix-strategies'),
      conversation_models: [$('#matrix-conversation-model').value],
      judge_models: [$('#matrix-judge-model').value],
      reps: Number($('#matrix-reps').value || 1),
      concurrency: Number($('#matrix-concurrency').value || 1),
    });
    status.innerHTML = statusBadge(job.status);
    renderJobPanel(job, panel);
    showToast('Matrix run started', 'success');
    window._pollers.matrix = setInterval(() => pollJob(job.id, 'matrix-job-panel', 'matrix-job-status', 'matrix'), 800);
  } catch (err) {
    panel.innerHTML = emptyState('Matrix failed', err.message);
    showToast(err.message, 'error');
  } finally {
    if (btn) { btn.classList.remove('btn-loading'); btn.disabled = false; }
  }
};

// ── Manual role-play ────────────────────────────────────────────

async function renderManual() {
  const options = await api('/config/run-options');
  const profileOpts = runSelectOptions(options.profiles, '');
  const strategyOpts = runSelectOptions(options.strategies, '');
  const conversationOpts = modelSelectOptions(options.conversation_models, options.defaults.conversation_model);
  const judgeOpts = modelSelectOptions(options.judge_models, options.defaults.judge_model);

  window._runOptions = options;
  mainEl.innerHTML = `
    <div class="page-header">
      <h1>Manual Run</h1>
      <p>Play the collector or debtor role, then save the judged transcript</p>
    </div>
    <div class="grid-2 manual-layout">
      <div class="card">
        <div class="card-header"><h2>Session Setup</h2></div>
        <div class="card-body">
          <form class="control-form" onsubmit="startManualSession(event)">
            ${selectField('manual-profile', 'Profile', profileOpts, "updateManualDescriptions()")}
            <p class="field-summary" id="manual-profile-summary"></p>
            ${selectField('manual-strategy', 'Strategy', strategyOpts, "updateManualDescriptions()")}
            <p class="field-summary" id="manual-strategy-summary"></p>
            ${selectField('manual-role', 'You play', '<option value="debtor">Debtor</option><option value="collector">Collector</option>')}
            ${advancedModelSettings('manual', conversationOpts, judgeOpts, 'AI model')}
            <button class="btn btn-primary" type="submit" id="manual-btn">Start session</button>
          </form>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><h2>Transcript</h2><div id="manual-status">${statusBadge('waiting_for_human')}</div></div>
        <div class="card-body" id="manual-panel">${emptyState('No Session', 'Start a manual session to begin.')}</div>
      </div>
    </div>`;
  updateManualDescriptions();
}

window.startManualSession = async function(event) {
  event.preventDefault();
  const panel = $('#manual-panel');
  const btn = $('#manual-btn');
  panel.innerHTML = skeleton();
  if (btn) { btn.classList.add('btn-loading'); btn.disabled = true; }
  try {
    const session = await apiPost('/manual-sessions', {
      profile_id: $('#manual-profile').value,
      strategy_id: $('#manual-strategy').value,
      human_role: $('#manual-role').value,
      conversation_model: $('#manual-conversation-model').value,
      judge_model: $('#manual-judge-model').value,
    });
    window._manualSessionId = session.id;
    renderManualSession(session);
    showToast('Session started', 'success');
  } catch (err) {
    panel.innerHTML = emptyState('Setup failed', err.message);
    showToast(err.message, 'error');
  } finally {
    if (btn) { btn.classList.remove('btn-loading'); btn.disabled = false; }
  }
};

window.submitManualTurn = async function(event) {
  event.preventDefault();
  const input = $('#manual-turn-content');
  const panel = $('#manual-panel');
  const content = input.value.trim();
  if (!content || !window._manualSessionId) return;
  input.value = '';
  panel.classList.add('is-loading');
  try {
    const session = await apiPost(`/manual-sessions/${window._manualSessionId}/turn`, { content });
    renderManualSession(session);
  } catch (err) {
    appendFormError(panel, err.message);
  } finally {
    panel.classList.remove('is-loading');
  }
};

window.finishManualSession = async function() {
  if (!window._manualSessionId) return;
  const panel = $('#manual-panel');
  try {
    const session = await apiPost(`/manual-sessions/${window._manualSessionId}/finish`, {});
    renderManualSession(session);
    showToast('Session finished and judged', 'success');
  } catch (err) {
    appendFormError(panel, err.message);
  }
};

function renderManualSession(session) {
  $('#manual-status').innerHTML = statusBadge(session.status);
  const run = session.run;
  const disabled = session.status !== 'waiting_for_human' ? 'disabled' : '';
  $('#manual-panel').innerHTML = `
    ${runMetaHTML(run)}
    ${transcriptHTML(run)}
    ${judgmentHTML(run)}
    ${session.status === 'completed' ? `
      <div class="btn-row" style="margin-top:var(--space-4)">
        ${linkButton('View saved run', `openTranscript(${jsArg(run.id)})`)}
      </div>` : `
      <form class="control-form" style="margin-top:var(--space-4)" onsubmit="submitManualTurn(event)">
        <label for="manual-turn-content" class="form-label">Your ${escapeHTML(session.human_role)} turn</label>
        <textarea class="form-textarea" id="manual-turn-content" rows="4" ${disabled} placeholder="Type your response as the ${escapeAttr(session.human_role)}."></textarea>
        <div class="btn-row">
          <button class="btn btn-primary" type="submit" ${disabled}>Send turn</button>
          <button class="btn btn-primary" type="button" onclick="finishManualSession()">Finish and judge</button>
        </div>
      </form>`}
    <p class="status-line" style="margin-top:var(--space-3)">${escapeHTML(session.message || '')}</p>`;
}

// ── Launch form helpers ─────────────────────────────────────────

window._pollers = {};

function selectField(id, label, optionsHTML, onchange = '') {
  const changeAttr = onchange ? ` onchange="${escapeAttr(onchange)}"` : '';
  return `
    <div class="form-field">
      <label for="${escapeAttr(id)}">${escapeHTML(label)}</label>
      <select class="filter-select" id="${escapeAttr(id)}"${changeAttr}>${optionsHTML}</select>
    </div>`;
}

function inputField(id, label, value, min, max, oninput = '') {
  const inputAttr = oninput ? ` oninput="${escapeAttr(oninput)}"` : '';
  return `
    <div class="form-field">
      <label for="${escapeAttr(id)}">${escapeHTML(label)}</label>
      <input class="form-input" id="${escapeAttr(id)}" type="number" value="${escapeAttr(value)}" min="${escapeAttr(min)}" max="${escapeAttr(max)}"${inputAttr}>
    </div>`;
}

function checkboxList(name, entries, selected = null) {
  return entries.map(([value, label]) => `
    <label class="check-option">
      <input type="checkbox" name="${escapeAttr(name)}" value="${escapeAttr(value)}" ${selected && !selected.includes(value) ? '' : 'checked'} onchange="updateMatrixCount()">
      <span>${escapeHTML(label)}</span>
    </label>`).join('');
}

function updateCheckboxSelection(name, selected) {
  $$(`input[name="${name}"]`).forEach(input => {
    input.checked = !selected || selected.includes(input.value);
  });
}

window.updateMatrixCount = function() {
  const profiles = checkedValues('matrix-profiles').length;
  const strategies = checkedValues('matrix-strategies').length;
  const reps = Number(($('#matrix-reps') || {}).value || 1);
  const total = profiles * strategies * reps;
  const el = $('#matrix-count');
  if (!el) return;
  el.classList.toggle('warning', total > 50);
  el.textContent = `${profiles} profiles x ${strategies} strategies x ${reps} reps = ${total} total simulations${total > 50 ? '. Large batches take longer and cost more.' : ''}`;
};

function checkedValues(name) {
  return $$(`input[name="${name}"]:checked`).map(input => input.value);
}

function appendFormError(container, message) {
  if (!container) return;
  const existing = $('.form-error', container);
  if (existing) existing.remove();
  $$('.status-line', container).forEach(status => status.remove());
  container.insertAdjacentHTML('beforeend', `<div class="form-error" role="alert">${escapeHTML(message)}</div>`);
}

function clearPoll(key) {
  if (window._pollers[key]) clearInterval(window._pollers[key]);
  delete window._pollers[key];
}

const _pollFailCounts = {};

async function pollJob(jobId, panelId, statusId, pollKey) {
  try {
    const job = await api(`/jobs/${pathPart(jobId)}`);
    if (_pollFailCounts[pollKey]) {
      _pollFailCounts[pollKey] = 0;
    }
    const panel = $(`#${panelId}`);
    const status = $(`#${statusId}`);
    if (status) status.innerHTML = statusBadge(job.status);
    if (panel) renderJobPanel(job, panel);
    if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
      clearPoll(pollKey);
      delete _pollFailCounts[pollKey];
      if (job.status === 'completed') showToast('Job completed', 'success');
      if (job.status === 'failed') showToast('Job failed', 'error');
      if (job.status === 'cancelled') showToast('Job cancelled', 'info');
    }
  } catch (_) {
    _pollFailCounts[pollKey] = (_pollFailCounts[pollKey] || 0) + 1;
    if (_pollFailCounts[pollKey] === 3) {
      showToast('Connection interrupted, retrying\u2026', 'error', 6000);
    }
  }
}

function renderJobPanel(job, panel) {
  const canCancel = job.status === 'queued' || job.status === 'running';
  panel.innerHTML = `
    <div class="status-card">
      <div class="job-item-head">
        <div>
          <div style="font-family:var(--font-mono);font-size:var(--text-xs);color:var(--text-secondary)">${escapeHTML(job.id)}</div>
          <div class="status-line">${escapeHTML(job.message || '')}</div>
        </div>
        ${statusBadge(job.status)}
      </div>
      ${progressHTML(job.completed, job.failed, job.total)}
      ${canCancel ? `<button class="btn btn-danger" type="button" onclick="cancelJob(${jsArg(job.id)})">Cancel job</button>` : ''}
      ${job.current_run ? `
        <div class="live-transcript">
          ${runMetaHTML(job.current_run)}
          ${transcriptHTML(job.current_run)}
          ${judgmentHTML(job.current_run)}
        </div>` : ''}
      ${job.result_ids && job.result_ids.length ? `
        <div class="btn-row" style="margin-top:var(--space-3)">
          ${linkButton('View latest run', `openTranscript(${jsArg(job.result_ids[job.result_ids.length - 1])})`)}
          ${linkButton('All runs', "navigateTo('runs')")}
        </div>` : ''}
      ${(job.errors || []).length ? `<div class="form-error" style="margin-top:var(--space-3)">${job.errors.map(escapeHTML).join('<br>')}</div>` : ''}
    </div>`;
}

window.cancelJob = async function(jobId) {
  const job = await apiPost(`/jobs/${pathPart(jobId)}/cancel`, {});
  const panels = ['single-job-panel', 'matrix-job-panel'];
  panels.forEach(id => {
    const panel = $(`#${id}`);
    if (panel) renderJobPanel(job, panel);
  });
};

function jobSummaryHTML(job) {
  return `
    <button class="job-item" type="button" onclick="showJob(${jsArg(job.id)}, 'matrix-job-panel', 'matrix-job-status')">
      <span style="font-size:var(--text-sm)">${escapeHTML(job.kind)} \u00b7 ${escapeHTML(job.id)}</span>
      <span>${statusBadge(job.status)}</span>
      <span style="font-size:var(--text-xs);color:var(--text-secondary)">${job.completed + job.failed} of ${job.total}</span>
    </button>`;
}

window.showJob = async function(jobId, panelId, statusId) {
  const job = await api(`/jobs/${pathPart(jobId)}`);
  const panel = $(`#${panelId}`);
  const status = $(`#${statusId}`);
  if (status) status.innerHTML = statusBadge(job.status);
  if (panel) renderJobPanel(job, panel);
};

// ── Transcript slideout ────────────────────────────────────────

window.openTranscript = async function(runId) {
  const overlay = $('#slideout-overlay');
  const panel = $('#slideout-panel');
  const body = $('#slideout-body');
  const title = $('#slideout-title');
  const subtitle = $('#slideout-subtitle');

  if (!panel.classList.contains('open')) _slideoutPreviousFocus = document.activeElement;
  window._currentTranscriptRunId = runId;
  overlay.classList.add('open');
  overlay.removeAttribute('aria-hidden');
  panel.classList.add('open');
  body.innerHTML = skeleton();
  title.textContent = 'Loading\u2026';
  subtitle.textContent = '';

  try {
    const run = await api(`/runs/${pathPart(runId)}`);
    title.textContent = run.id;
    subtitle.textContent = `${fmtId(run.profile_id)} \u00d7 ${fmtId(run.strategy_id)}`;

    body.innerHTML = runMetaHTML(run) + transcriptHTML(run) + judgmentHTML(run);
    renderSlideoutNav(runId);

    panel.querySelector('.slideout-close').focus();
  } catch (err) {
    body.innerHTML = emptyState('Error', err.message);
  }
};

function renderSlideoutNav(runId) {
  let nav = $('#slideout-nav');
  const header = $('.slideout-header');
  if (!nav && header) {
    nav = document.createElement('div');
    nav.id = 'slideout-nav';
    nav.className = 'slideout-nav';
    header.insertBefore(nav, header.querySelector('.slideout-close'));
  }
  if (!nav) return;
  const runs = window._filteredRuns || window._allRuns || [];
  const index = runs.findIndex(run => run.id === runId);
  if (index === -1 || runs.length < 2) {
    nav.innerHTML = '';
    return;
  }
  nav.innerHTML = `
    <button class="btn" type="button" ${index === 0 ? 'disabled' : ''} onclick="openTranscript(${jsArg(runs[index - 1]?.id || '')})">Previous</button>
    <button class="btn" type="button" ${index === runs.length - 1 ? 'disabled' : ''} onclick="openTranscript(${jsArg(runs[index + 1]?.id || '')})">Next</button>`;
}

function runMetaHTML(run) {
  return `
      <div class="meta-tags">
        <span class="meta-tag"><strong>Status:</strong> ${escapeHTML(run.status)}</span>
        <span class="meta-tag"><strong>Model:</strong> ${escapeHTML(run.conversation_model)}</span>
        <span class="meta-tag"><strong>Turns:</strong> ${run.turn_count}</span>
        <span class="meta-tag"><strong>Ended by:</strong> ${run.ended_by ? escapeHTML(fmtId(run.ended_by)) : '\u2014'}</span>
        <span class="meta-tag"><strong>Tokens:</strong> ${fmtNum(run.total_input_tokens + run.total_output_tokens)}</span>
        <span class="meta-tag"><strong>Cost:</strong> ${fmtMoney(run.estimated_cost_usd)}</span>
      </div>`;
}

function transcriptHTML(run) {
  const chatMsgs = chatHTML(run.transcript || '');
  return `<div class="chat-container" role="list" aria-label="Conversation transcript">${chatMsgs || emptyState('No Turns', 'No transcript turns yet.')}</div>`;
}

function judgmentHTML(run) {
  if (!run.judgment) return '';
  const j = run.judgment;
  const violations = (j.constraint_violations || []);
  return `
        <div class="judgment-panel">
          <h3>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            Judgment ${outcomeBadge(j.payment_outcome)}
          </h3>
          <div class="judgment-scores">
            ${scoreBarHTML('Payment Probability', j.payment_probability)}
            ${scoreBarHTML('Compliance Score', j.compliance_score)}
            ${scoreBarHTML('Debtor Satisfaction', j.debtor_satisfaction)}
            ${scoreBarHTML('Rapport Built', j.rapport_built)}
            ${scoreBarHTML('Escalation Risk', j.escalation_risk)}
            ${scoreBarHTML('Efficiency', Math.min(1, (j.conversation_efficiency || 0) / 20))}
          </div>
          ${violations.length ? `
            <div class="judgment-violations" aria-label="Constraint violations">
              ${violations.map(v => `<span class="badge badge-danger">${escapeHTML(v)}</span>`).join('')}
            </div>` : ''}
          ${j.reasoning ? `<div class="judgment-reasoning">${escapeHTML(j.reasoning)}</div>` : ''}
        </div>`;
}

window.closeTranscript = function() {
  const overlay = $('#slideout-overlay');
  const panel = $('#slideout-panel');
  overlay.classList.remove('open');
  overlay.setAttribute('aria-hidden', 'true');
  panel.classList.remove('open');
  const nav = $('#slideout-nav');
  if (nav) nav.innerHTML = '';
  if (_slideoutPreviousFocus && typeof _slideoutPreviousFocus.focus === 'function') {
    _slideoutPreviousFocus.focus();
    _slideoutPreviousFocus = null;
  }
};

document.addEventListener('keydown', (e) => {
  const panel = $('#slideout-panel');
  if (e.key === 'Tab' && panel && panel.classList.contains('open')) {
    const focusable = $$('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])', panel).filter(el => !el.disabled);
    if (focusable.length) {
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }
  if (e.key === 'Escape') {
    const sidebar = $('#sidebar');
    if (sidebar && sidebar.classList.contains('open')) {
      closeMobileSidebar();
      return;
    }
    closeTranscript();
  }
});

// ── Playbook ───────────────────────────────────────────────────

async function renderPlaybook() {
  const data = await api('/playbook?format=html');

  mainEl.innerHTML = `
    <div class="page-header page-header-actions">
      <div>
        <h1>Generated Playbook</h1>
        <p>Strategy recommendations based on simulation data</p>
      </div>
      <div class="btn-row">
        <button class="btn" type="button" onclick="copyPlaybook()">Copy Markdown</button>
        <button class="btn" type="button" onclick="exportPlaybook()">Export Markdown</button>
      </div>
    </div>
    <div class="card">
      <div class="card-body">
        <article class="playbook-content">${data.content || emptyState('No Playbook', 'Run simulations and analyze to generate a playbook.')}</article>
      </div>
    </div>
  `;
}

window.exportPlaybook = async function() {
  const data = await api('/playbook?format=markdown');
  downloadText('collection-swarm-playbook.md', data.content || '', 'text/markdown;charset=utf-8');
};

window.copyPlaybook = async function() {
  const data = await api('/playbook?format=markdown');
  await navigator.clipboard.writeText(data.content || '');
  showToast('Playbook copied', 'success');
};

function downloadText(filename, text, type) {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ── Compliance ─────────────────────────────────────────────────

async function renderCompliance() {
  const data = await api('/compliance/exclusions');
  const exclusions = data.exclusions || [];
  const thresholds = data.thresholds || {};
  const thresholdText = `Excluded when compliance < ${pct(thresholds.min_compliance_score || 0)} or escalation risk > ${pct(thresholds.max_escalation_risk || 0)}.`;

  let content;
  if (!exclusions.length) {
    const lowCoverage = (data.total_completed_runs || 0) < (data.minimum_runs_per_combination || 3);
    content = `
      <div class="card">
        <div class="card-body">
          <div class="empty-state" role="status">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4" stroke="var(--success)"/></svg>
            <h3>All Clear</h3>
            <p>All combinations clear across ${fmtNum(data.total_completed_runs || 0)} completed runs. ${lowCoverage ? 'Some combinations have fewer than 3 data points; additional runs would increase confidence.' : 'Coverage meets the current confidence target.'}</p>
          </div>
        </div>
      </div>`;
  } else {
    const cards = exclusions.map(e => `
      <div class="exclusion-card" role="alert">
        <h4>${escapeHTML(fmtId(e.strategy_id))} \u00d7 ${escapeHTML(fmtId(e.profile_id))}</h4>
        <div class="exclusion-stats">
          <div class="exclusion-stat">
            <span class="exclusion-stat-label">Compliance</span>
            <span class="exclusion-stat-value ${scoreClass(e.compliance_score)}">${pct(e.compliance_score)}</span>
            <span class="threshold-line">Threshold ${pct(thresholds.min_compliance_score || 0)}</span>
          </div>
          <div class="exclusion-stat">
            <span class="exclusion-stat-label">Escalation</span>
            <span class="exclusion-stat-value ${scoreClass(1 - e.escalation_risk)}">${pct(e.escalation_risk)}</span>
            <span class="threshold-line">Max ${pct(thresholds.max_escalation_risk || 0)}</span>
          </div>
        </div>
        <p class="status-line">Based on ${fmtNum(e.simulation_count || 0)} simulations</p>
        ${(e.run_ids || []).length ? `<div class="evidence-links">${e.run_ids.map(id => `<button class="text-link" type="button" onclick="openTranscript(${jsArg(id)})">View evidence ${escapeHTML(id)}</button>`).join('')}</div>` : ''}
        <div class="exclusion-detail">${escapeHTML(e.reason)}</div>
      </div>
    `).join('');
    content = `<div class="grid-2">${cards}</div>`;
  }

  mainEl.innerHTML = `
    <div class="page-header">
      <h1>Compliance Monitor</h1>
      <p>${thresholdText}</p>
    </div>
    ${content}
  `;
}

// ── Profiles ───────────────────────────────────────────────────

async function renderProfiles() {
  const profiles = await api('/config/profiles');

  const archetypeColors = {
    cooperative: '--chart-7',
    avoidant: '--chart-6',
    hostile: '--chart-5',
    disputer: '--chart-4',
    confused: '--chart-3',
  };

  const cards = profiles.map(p => {
    const colorVar = archetypeColors[p.archetype] || '--chart-1';
    return `
    <div class="config-card">
      <div class="config-card-header">
        <div class="config-card-icon" style="background:var(${colorVar});color:oklch(99% 0 0);font-weight:700;font-size:var(--text-sm)">${escapeHTML(fmtId(p.archetype).charAt(0))}</div>
        <h3>${escapeHTML(fmtId(p.id))}</h3>
      </div>
      <div class="config-field"><span class="config-field-key">Archetype</span><span class="config-field-value">${escapeHTML(fmtId(p.archetype))}</span></div>
      <div class="config-field"><span class="config-field-key">Debt</span><span class="config-field-value">$${p.debt_amount.toLocaleString()} ${escapeHTML(p.debt_type)}</span></div>
      <div class="config-field"><span class="config-field-key">Age</span><span class="config-field-value">${p.debt_age_days} days</span></div>
      <div class="config-field"><span class="config-field-key">Prior Contacts</span><span class="config-field-value">${p.prior_contact_count}</span></div>
      <div class="config-field"><span class="config-field-key">Emotional State</span><span class="config-field-value">${escapeHTML(fmtId(p.emotional_state))}</span></div>
      <div class="config-field"><span class="config-field-key">Objection</span><span class="config-field-value">${escapeHTML(fmtId(p.primary_objection))}</span></div>
      <div class="config-field"><span class="config-field-key">Responsiveness</span><span class="config-field-value">${escapeHTML(fmtId(p.responsiveness))}</span></div>
      <div class="config-field"><span class="config-field-key">Demographics</span><span class="config-field-value">${escapeHTML(fmtId(p.demographics))}</span></div>
      ${performanceSummaryHTML(p.performance)}
      ${p.backstory ? `<div class="config-backstory">${escapeHTML(p.backstory.trim())}</div>` : ''}
      ${p.constraints && p.constraints.length ? `
        <div class="config-constraints">
          ${p.constraints.map(c => `<div class="config-constraint">${escapeHTML(c.text)}</div>`).join('')}
        </div>` : ''}
      <div class="btn-row config-actions">
        <button class="btn btn-primary" type="button" onclick="navigateTo('launch', { profile: ${jsArg(p.id)} })">Run simulation</button>
        <button class="btn" type="button" onclick="navigateTo('matrix', { profile: ${jsArg(p.id)} })">Compare strategies</button>
      </div>
    </div>
  `;
  }).join('');

  mainEl.innerHTML = `
    <div class="page-header">
      <h1>Debtor Profiles</h1>
      <p>${profiles.length} configured debtor archetype${profiles.length !== 1 ? 's' : ''}</p>
    </div>
    <div class="grid-3">${cards}</div>
  `;
}

// ── Strategies ─────────────────────────────────────────────────

async function renderStrategies() {
  const strategies = await api('/config/strategies');

  const toneColors = {
    empathetic: '--chart-7',
    assertive: '--chart-5',
    neutral: '--chart-1',
    urgent: '--chart-6',
  };

  const cards = strategies.map(s => {
    const colorVar = toneColors[s.tone] || '--chart-2';
    return `
    <div class="config-card">
      <div class="config-card-header">
        <div class="config-card-icon" style="background:var(${colorVar});color:oklch(99% 0 0);font-weight:700;font-size:var(--text-sm)">${escapeHTML(fmtId(s.tone).charAt(0))}</div>
        <h3>${escapeHTML(fmtId(s.id))}</h3>
      </div>
      <div class="config-field"><span class="config-field-key">Tone</span><span class="config-field-value">${escapeHTML(fmtId(s.tone))}</span></div>
      <div class="config-field"><span class="config-field-key">Opening</span><span class="config-field-value">${escapeHTML(fmtId(s.opening_approach))}</span></div>
      <div class="config-field"><span class="config-field-key">Negotiation</span><span class="config-field-value">${escapeHTML(fmtId(s.negotiation_tactic))}</span></div>
      <div class="config-field"><span class="config-field-key">Escalation</span><span class="config-field-value">${escapeHTML(fmtId(s.escalation_style))}</span></div>
      <div class="config-field"><span class="config-field-key">Concessions</span><span class="config-field-value">${escapeHTML(fmtId(s.concession_willingness))}</span></div>
      <div class="config-field"><span class="config-field-key">Compliance</span><span class="config-field-value">${escapeHTML(fmtId(s.compliance_adherence))}</span></div>
      <div class="config-field"><span class="config-field-key">Follow-up</span><span class="config-field-value">${escapeHTML(fmtId(s.follow_up_strategy))}</span></div>
      ${performanceSummaryHTML(s.performance)}
      <div class="btn-row config-actions">
        <button class="btn btn-primary" type="button" onclick="navigateTo('launch', { strategy: ${jsArg(s.id)} })">Launch with this strategy</button>
      </div>
    </div>
  `;
  }).join('');

  mainEl.innerHTML = `
    <div class="page-header">
      <h1>Collector Strategies</h1>
      <p>${strategies.length} configured collection strateg${strategies.length !== 1 ? 'ies' : 'y'}</p>
    </div>
    <div class="grid-2">${cards}</div>
  `;
}

// ══════════════════════════════════════════════════════════════
//  Bootstrap
// ══════════════════════════════════════════════════════════════

(function init() {
  const hash = location.hash.replace('#', '') || 'dashboard';
  navigateTo(hash);
})();
