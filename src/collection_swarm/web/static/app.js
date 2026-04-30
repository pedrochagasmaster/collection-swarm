/* ═══════════════════════════════════════════════════════════════
   Collection Swarm — Single-Page Application
   Impeccable edition: skeleton loading, overview strip (no hero-
   metric template), capped stagger, ARIA management.
   ═══════════════════════════════════════════════════════════════ */

const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];
const mainEl = $('#main-content');

// ── Routing ────────────────────────────────────────────────────

let currentPage = 'dashboard';

function navigateTo(page, params = {}) {
  currentPage = page;
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
}

(function initTheme() {
  const saved = localStorage.getItem('cs-theme');
  if (saved) document.documentElement.dataset.theme = saved;
})();

// ── Data fetching ──────────────────────────────────────────────

async function api(path) {
  const res = await fetch(`/api${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ── Helpers ────────────────────────────────────────────────────

function pct(v) { return `${Math.round(v * 100)}%`; }
function scoreClass(v) { return v >= 0.7 ? 'score-good' : v >= 0.4 ? 'score-mid' : 'score-bad'; }
function fmtId(id) { return id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }
function fmtMoney(v) { return `$${v.toFixed(4)}`; }
function fmtNum(v) { return Number(v).toLocaleString(); }
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
      <h3>${title}</h3>
      <p>${msg}</p>
    </div>`;
}

function scoreBarHTML(label, value) {
  const cls = scoreClass(value);
  const colorVar = cls === 'score-good' ? '--success' : cls === 'score-mid' ? '--warning' : '--danger';
  return `
    <div class="judgment-score-item">
      <span class="judgment-score-label">${label}</span>
      <div class="score-bar-wrap">
        <div class="score-bar" role="meter" aria-valuenow="${Math.round(value * 100)}" aria-valuemin="0" aria-valuemax="100" aria-label="${label}">
          <div class="score-bar-fill" style="width:${value * 100}%;background:var(${colorVar})"></div>
        </div>
        <span class="score-bar-label ${cls}">${pct(value)}</span>
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
  return `<span class="badge ${map[outcome] || 'badge-neutral'}">${fmtId(outcome)}</span>`;
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

// ══════════════════════════════════════════════════════════════
//  PAGE RENDERERS
// ══════════════════════════════════════════════════════════════

async function renderPage(page, params = {}) {
  mainEl.innerHTML = skeleton();
  try {
    switch (page) {
      case 'dashboard': await renderDashboard(); break;
      case 'runs': await renderRuns(); break;
      case 'playbook': await renderPlaybook(); break;
      case 'compliance': await renderCompliance(); break;
      case 'profiles': await renderProfiles(); break;
      case 'strategies': await renderStrategies(); break;
      default: mainEl.innerHTML = emptyState('Not Found', 'Page not found.');
    }
  } catch (err) {
    mainEl.innerHTML = emptyState('Error', err.message);
  }
}

// ── Dashboard ──────────────────────────────────────────────────

async function renderDashboard() {
  const data = await api('/dashboard');
  const { total_runs, completed, failed, average_scores: avg, outcome_distribution: dist, cost } = data;

  const totalOutcomes = Object.values(dist).reduce((a, b) => a + b, 0) || 1;

  let outcomeRows = '';
  const sortedOutcomes = Object.entries(dist).sort((a, b) => b[1] - a[1]);
  for (const [outcome, count] of sortedOutcomes) {
    const w = (count / totalOutcomes) * 100;
    const color = OUTCOME_COLORS[outcome] || 'var(--chart-1)';
    outcomeRows += `
      <div class="dist-row">
        <span class="dist-label">${fmtId(outcome)}</span>
        <div class="dist-bar-track">
          <div class="dist-bar-fill" style="width:${Math.max(w, 6)}%;background:${color}"><span>${pct(count/totalOutcomes)}</span></div>
        </div>
        <span class="dist-count">${count}</span>
      </div>`;
  }

  let strategySection = '';
  if (data.profiles.length) {
    const tabs = data.profiles.map((p, i) =>
      `<button class="tab-btn${i === 0 ? ' active' : ''}" onclick="switchProfileTab('${p}', this)" role="tab" aria-selected="${i === 0}">${fmtId(p)}</button>`
    ).join('');
    strategySection = `
      <div class="card" style="margin-top:var(--space-8)">
        <div class="card-header"><h2>Strategy Rankings</h2></div>
        <div class="card-body">
          <div class="tabs" role="tablist" aria-label="Profile strategy rankings" id="profile-tabs">${tabs}</div>
          <div id="strategy-comparison" role="tabpanel">${skeleton()}</div>
        </div>
      </div>`;
    setTimeout(() => loadStrategyComparison(data.profiles[0]), 0);
  }

  mainEl.innerHTML = `
    <div class="page-header">
      <h1>Dashboard</h1>
      <p>Overview of simulation results and performance metrics</p>
    </div>

    <div class="overview-strip" role="status" aria-label="Simulation summary">
      <div class="overview-item">
        <span class="overview-label">Runs</span>
        <span class="overview-value">${fmtNum(total_runs)}</span>
      </div>
      <div class="overview-sep" aria-hidden="true"></div>
      <div class="overview-item">
        <span class="overview-label">Completed</span>
        <span class="overview-value">${fmtNum(completed)}</span>
      </div>
      <div class="overview-sep" aria-hidden="true"></div>
      <div class="overview-item">
        <span class="overview-label">Failed</span>
        <span class="overview-value">${fmtNum(failed)}</span>
      </div>
      <div class="overview-sep" aria-hidden="true"></div>
      <div class="overview-item">
        <span class="overview-label">Cost</span>
        <span class="overview-value">${fmtMoney(cost.estimated_cost_usd || 0)}</span>
      </div>
      <div class="overview-sep" aria-hidden="true"></div>
      <div class="overview-item">
        <span class="overview-label">Tokens</span>
        <span class="overview-value">${fmtNum((cost.input_tokens || 0) + (cost.output_tokens || 0))}</span>
      </div>
    </div>

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

    ${strategySection}
  `;
}

window.switchProfileTab = async function(profileId, btn) {
  $$('#profile-tabs .tab-btn').forEach(b => {
    b.classList.remove('active');
    b.setAttribute('aria-selected', 'false');
  });
  btn.classList.add('active');
  btn.setAttribute('aria-selected', 'true');
  await loadStrategyComparison(profileId);
};

async function loadStrategyComparison(profileId) {
  const container = $('#strategy-comparison');
  if (!container) return;
  container.innerHTML = skeleton();
  try {
    const data = await api(`/profiles/${profileId}/strategies`);
    if (!data.strategies.length) {
      container.innerHTML = emptyState('No Data', `No completed simulations for ${fmtId(profileId)}.`);
      return;
    }
    container.innerHTML = data.strategies.map((s, i) => `
      <div class="comparison-row">
        <div class="comparison-rank" aria-label="Rank ${i + 1}">${i + 1}</div>
        <div class="comparison-name">${fmtId(s.strategy_id)}</div>
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
            <span class="comparison-metric-value ${scoreClass(1 - s.mean_escalation_risk)}">${pct(s.mean_escalation_risk)}</span>
            <span class="comparison-metric-label">Escalation</span>
          </div>
          <div class="comparison-metric">
            <span class="comparison-metric-value">${s.simulation_count}</span>
            <span class="comparison-metric-label">Runs</span>
          </div>
        </div>
      </div>
    `).join('');
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

  const profileOpts = profiles.map(p => `<option value="${p}">${fmtId(p)}</option>`).join('');
  const strategyOpts = strategies.map(s => `<option value="${s}">${fmtId(s)}</option>`).join('');

  mainEl.innerHTML = `
    <div class="page-header">
      <h1>Simulation Runs</h1>
      <p>${runs.length} simulation${runs.length !== 1 ? 's' : ''} recorded</p>
    </div>

    <div class="filter-bar" role="search" aria-label="Filter simulations">
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
    </div>

    <div class="card">
      <div class="card-body no-padding">
        <div style="overflow-x:auto;max-height:calc(100vh - 280px)">
          <table class="data-table" id="runs-table" aria-label="Simulation runs">
            <thead>
              <tr>
                <th scope="col">ID</th>
                <th scope="col">Status</th>
                <th scope="col">Profile</th>
                <th scope="col">Strategy</th>
                <th scope="col">Outcome</th>
                <th scope="col">Payment</th>
                <th scope="col">Compliance</th>
                <th scope="col">Turns</th>
                <th scope="col">Ended By</th>
                <th scope="col">Time</th>
              </tr>
            </thead>
            <tbody id="runs-tbody"></tbody>
          </table>
        </div>
      </div>
    </div>
  `;

  window._allRuns = runs;
  filterRuns();
}

window.filterRuns = function() {
  const status = ($('#filter-status') || {}).value || '';
  const profile = ($('#filter-profile') || {}).value || '';
  const strategy = ($('#filter-strategy') || {}).value || '';

  let filtered = window._allRuns || [];
  if (status) filtered = filtered.filter(r => r.status === status);
  if (profile) filtered = filtered.filter(r => r.profile_id === profile);
  if (strategy) filtered = filtered.filter(r => r.strategy_id === strategy);

  const tbody = $('#runs-tbody');
  if (!tbody) return;

  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="10">${emptyState('No Runs', 'No simulations match the current filters.')}</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.slice().reverse().map(r => {
    const j = r.judgment;
    return `
      <tr onclick="openTranscript('${r.id}')" tabindex="0" role="button" aria-label="View transcript for ${r.id}" onkeydown="if(event.key==='Enter')openTranscript('${r.id}')">
        <td>${r.id}</td>
        <td><span class="badge ${r.status === 'completed' ? 'badge-success' : 'badge-danger'}">${r.status}</span></td>
        <td>${fmtId(r.profile_id)}</td>
        <td>${fmtId(r.strategy_id)}</td>
        <td>${j ? outcomeBadge(j.payment_outcome) : '\u2014'}</td>
        <td class="${j ? scoreClass(j.payment_probability) : ''}">${j ? pct(j.payment_probability) : '\u2014'}</td>
        <td class="${j ? scoreClass(j.compliance_score) : ''}">${j ? pct(j.compliance_score) : '\u2014'}</td>
        <td>${r.turn_count}</td>
        <td>${r.ended_by ? fmtId(r.ended_by) : '\u2014'}</td>
        <td>${relTime(r.started_at)}</td>
      </tr>`;
  }).join('');
};

// ── Transcript slideout ────────────────────────────────────────

window.openTranscript = async function(runId) {
  const overlay = $('#slideout-overlay');
  const panel = $('#slideout-panel');
  const body = $('#slideout-body');
  const title = $('#slideout-title');
  const subtitle = $('#slideout-subtitle');

  overlay.classList.add('open');
  overlay.removeAttribute('aria-hidden');
  panel.classList.add('open');
  body.innerHTML = skeleton();
  title.textContent = 'Loading\u2026';
  subtitle.textContent = '';

  try {
    const run = await api(`/runs/${runId}`);
    title.textContent = run.id;
    subtitle.textContent = `${fmtId(run.profile_id)} \u00d7 ${fmtId(run.strategy_id)}`;

    const metaTags = `
      <div class="meta-tags">
        <span class="meta-tag"><strong>Status:</strong> ${run.status}</span>
        <span class="meta-tag"><strong>Model:</strong> ${run.conversation_model}</span>
        <span class="meta-tag"><strong>Turns:</strong> ${run.turn_count}</span>
        <span class="meta-tag"><strong>Ended by:</strong> ${run.ended_by ? fmtId(run.ended_by) : '\u2014'}</span>
        <span class="meta-tag"><strong>Tokens:</strong> ${fmtNum(run.total_input_tokens + run.total_output_tokens)}</span>
        <span class="meta-tag"><strong>Cost:</strong> ${fmtMoney(run.estimated_cost_usd)}</span>
      </div>`;

    const MAX_STAGGER = 10;
    const chatMsgs = (run.transcript || []).map((m, i) => {
      const avatarMap = { collector: 'C', debtor: 'D', system: 'S', judge: 'J' };
      const delay = Math.min(i, MAX_STAGGER) * 40;
      return `
        <div class="chat-msg ${m.role}" style="animation-delay:${delay}ms" role="listitem">
          <div class="chat-avatar" aria-hidden="true">${avatarMap[m.role] || '?'}</div>
          <div class="chat-bubble">
            <div class="chat-role">${m.role}</div>
            ${m.content}
          </div>
        </div>`;
    }).join('');

    let judgmentHTML = '';
    if (run.judgment) {
      const j = run.judgment;
      const violations = (j.constraint_violations || []);
      judgmentHTML = `
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
              ${violations.map(v => `<span class="badge badge-danger">${v}</span>`).join('')}
            </div>` : ''}
          ${j.reasoning ? `<div class="judgment-reasoning">${j.reasoning}</div>` : ''}
        </div>`;
    }

    body.innerHTML = metaTags + `<div class="chat-container" role="list" aria-label="Conversation transcript">${chatMsgs}</div>` + judgmentHTML;

    panel.querySelector('.slideout-close').focus();
  } catch (err) {
    body.innerHTML = emptyState('Error', err.message);
  }
};

window.closeTranscript = function() {
  const overlay = $('#slideout-overlay');
  const panel = $('#slideout-panel');
  overlay.classList.remove('open');
  overlay.setAttribute('aria-hidden', 'true');
  panel.classList.remove('open');
};

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeTranscript();
});

// ── Playbook ───────────────────────────────────────────────────

async function renderPlaybook() {
  const data = await api('/playbook?format=html');

  mainEl.innerHTML = `
    <div class="page-header">
      <h1>Generated Playbook</h1>
      <p>Strategy recommendations based on simulation data</p>
    </div>
    <div class="card">
      <div class="card-body">
        <article class="playbook-content">${data.content || emptyState('No Playbook', 'Run simulations and analyze to generate a playbook.')}</article>
      </div>
    </div>
  `;
}

// ── Compliance ─────────────────────────────────────────────────

async function renderCompliance() {
  const exclusions = await api('/compliance/exclusions');

  let content;
  if (!exclusions.length) {
    content = `
      <div class="card">
        <div class="card-body">
          <div class="empty-state" role="status">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4" stroke="var(--success)"/></svg>
            <h3>All Clear</h3>
            <p>No compliance exclusions detected. All strategy-profile combinations meet the configured thresholds.</p>
          </div>
        </div>
      </div>`;
  } else {
    const cards = exclusions.map(e => `
      <div class="exclusion-card" role="alert">
        <h4>${fmtId(e.strategy_id)} \u00d7 ${fmtId(e.profile_id)}</h4>
        <div class="exclusion-detail">
          <strong>Compliance:</strong> ${pct(e.compliance_score)} &nbsp;|&nbsp; <strong>Escalation Risk:</strong> ${pct(e.escalation_risk)}
        </div>
        <div class="exclusion-detail">${e.reason}</div>
      </div>
    `).join('');
    content = `<div class="grid-2">${cards}</div>`;
  }

  mainEl.innerHTML = `
    <div class="page-header">
      <h1>Compliance Monitor</h1>
      <p>Strategy-profile combinations flagged for compliance or escalation risk concerns</p>
    </div>
    ${content}
  `;
}

// ── Profiles ───────────────────────────────────────────────────

async function renderProfiles() {
  const profiles = await api('/config/profiles');

  const cards = profiles.map(p => `
    <div class="config-card">
      <h3>${fmtId(p.id)}</h3>
      <div class="config-field"><span class="config-field-key">Archetype</span><span class="config-field-value">${fmtId(p.archetype)}</span></div>
      <div class="config-field"><span class="config-field-key">Debt</span><span class="config-field-value">$${p.debt_amount.toLocaleString()} ${p.debt_type}</span></div>
      <div class="config-field"><span class="config-field-key">Age</span><span class="config-field-value">${p.debt_age_days} days</span></div>
      <div class="config-field"><span class="config-field-key">Prior Contacts</span><span class="config-field-value">${p.prior_contact_count}</span></div>
      <div class="config-field"><span class="config-field-key">Emotional State</span><span class="config-field-value">${fmtId(p.emotional_state)}</span></div>
      <div class="config-field"><span class="config-field-key">Objection</span><span class="config-field-value">${fmtId(p.primary_objection)}</span></div>
      <div class="config-field"><span class="config-field-key">Responsiveness</span><span class="config-field-value">${fmtId(p.responsiveness)}</span></div>
      <div class="config-field"><span class="config-field-key">Demographics</span><span class="config-field-value">${fmtId(p.demographics)}</span></div>
      ${p.backstory ? `<div class="config-backstory">${p.backstory.trim()}</div>` : ''}
      ${p.constraints && p.constraints.length ? `
        <div class="config-constraints">
          ${p.constraints.map(c => `<div class="config-constraint">${c.text}</div>`).join('')}
        </div>` : ''}
    </div>
  `).join('');

  mainEl.innerHTML = `
    <div class="page-header">
      <h1>Debtor Profiles</h1>
      <p>Configured debtor archetypes used in simulations</p>
    </div>
    <div class="grid-3">${cards}</div>
  `;
}

// ── Strategies ─────────────────────────────────────────────────

async function renderStrategies() {
  const strategies = await api('/config/strategies');

  const cards = strategies.map(s => `
    <div class="config-card">
      <h3>${fmtId(s.id)}</h3>
      <div class="config-field"><span class="config-field-key">Tone</span><span class="config-field-value">${fmtId(s.tone)}</span></div>
      <div class="config-field"><span class="config-field-key">Opening</span><span class="config-field-value">${fmtId(s.opening_approach)}</span></div>
      <div class="config-field"><span class="config-field-key">Negotiation</span><span class="config-field-value">${fmtId(s.negotiation_tactic)}</span></div>
      <div class="config-field"><span class="config-field-key">Escalation</span><span class="config-field-value">${fmtId(s.escalation_style)}</span></div>
      <div class="config-field"><span class="config-field-key">Concessions</span><span class="config-field-value">${fmtId(s.concession_willingness)}</span></div>
      <div class="config-field"><span class="config-field-key">Compliance</span><span class="config-field-value">${fmtId(s.compliance_adherence)}</span></div>
      <div class="config-field"><span class="config-field-key">Follow-up</span><span class="config-field-value">${fmtId(s.follow_up_strategy)}</span></div>
    </div>
  `).join('');

  mainEl.innerHTML = `
    <div class="page-header">
      <h1>Collector Strategies</h1>
      <p>Configured collection strategies used in simulations</p>
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
