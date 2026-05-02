/* ═══════════════════════════════════════════════════════════════
   Collection Swarm — Arena & Config Module
   Compliance monitor, Elo arena, evolution pool, calibration,
   debtor profiles, collector strategies, and app bootstrap.
   Depends on core.js and pages.js.
   ═══════════════════════════════════════════════════════════════ */

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
        <p class="status-line">Based on ${fmtNum(e.simulation_count || 0)} simulations across ${(e.model_pairs || []).length || 1} model pairing${((e.model_pairs || []).length || 1) !== 1 ? 's' : ''}</p>
        ${(e.model_pairs || []).length ? `<div class="model-pairings">${e.model_pairs.map(model => `<span>${escapeHTML(model.conversation_model)} + ${escapeHTML(model.judge_model)}</span>`).join('')}</div>` : ''}
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

// ── Arena ───────────────────────────────────────────────────────

async function renderArena() {
  const [leaderboard, options, jobs, tournaments] = await Promise.all([
    api('/arena/leaderboard'),
    api('/config/run-options'),
    api('/jobs'),
    api('/arena/tournaments'),
  ]);
  const strategies = checkboxList('arena-strategies', options.strategies.map(s => [s.id, fmtId(s.id)]));
  const profiles = checkboxList('arena-profiles', options.profiles.map(p => [p.id, fmtId(p.id)]));
  const conversationOpts = modelSelectOptions(options.conversation_models, options.defaults.conversation_model);
  const judgeOpts = modelSelectOptions(options.judge_models, options.defaults.judge_model);
  const tournamentJobs = jobs.filter(job => job.kind === 'tournament');

  mainEl.innerHTML = `
    <div class="page-header">
      <h1>Arena</h1>
      <p>Elo-rated tournaments rank strategies by debtor difficulty and profiles by resistance.</p>
    </div>
    <div class="grid-2">
      <div class="card">
        <div class="card-header"><h2>Launch Tournament</h2></div>
        <div class="card-body">
          <form class="control-form" onsubmit="startArenaTournament(event)">
            ${selectField('arena-format', 'Format', '<option value="swiss">Swiss</option><option value="round_robin">Round robin</option>', "updateArenaCount()")}
            <div class="btn-row">
              ${inputField('arena-rounds', 'Rounds', 4, 1, 20, "updateArenaCount()")}
              ${inputField('arena-reps', 'Reps per pairing', 1, 1, 10, "updateArenaCount()")}
              ${inputField('arena-concurrency', 'Concurrency', 2, 1, 10)}
            </div>
            <div class="form-field"><label>Strategies</label><div class="checkbox-grid" onchange="updateArenaCount()">${strategies}</div></div>
            <div class="form-field"><label>Profiles</label><div class="checkbox-grid" onchange="updateArenaCount()">${profiles}</div></div>
            ${advancedModelSettings('arena', conversationOpts, judgeOpts)}
            <div class="matrix-count" id="arena-count" aria-live="polite"></div>
            <button class="btn btn-primary" id="arena-btn" type="submit">Start tournament</button>
          </form>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><h2>Progress</h2><div id="arena-job-status">${statusBadge('queued')}</div></div>
        <div class="card-body" id="arena-job-panel">
          ${tournamentJobs.length ? tournamentJobs.map(jobSummaryHTML).join('') : emptyState('No Tournaments', 'Start a tournament to update Elo ratings.')}
        </div>
      </div>
    </div>
    <div class="grid-2">
      ${arenaLeaderboardCard('Strategy Leaderboard', leaderboard.strategies || [])}
      ${arenaLeaderboardCard('Profile Leaderboard', leaderboard.profiles || [])}
    </div>
    <section class="card">
      <div class="card-header"><h2>Recent Tournaments</h2></div>
      <div class="card-body">
        ${tournaments.length ? tournaments.slice(0, 6).map(t => `<div class="job-summary"><span>${escapeHTML(t.id)}</span><span>${fmtNum(t.total_games)} games · ${fmtId(t.config.format)}</span></div>`).join('') : emptyState('No Tournament History', 'Completed tournaments will appear here.')}
      </div>
    </section>`;
  updateArenaCount();
}

function arenaLeaderboardCard(title, ratings) {
  const rows = ratings.map((rating, index) => `
    <tr tabindex="0" role="button" aria-label="Toggle history for ${escapeAttr(fmtId(rating.entity_id))}" onclick="toggleArenaHistory(${jsArg(rating.entity_id)})" onkeydown="handleArenaRowKey(event, ${jsArg(rating.entity_id)})">
      <td>${index + 1}</td>
      <td>${escapeHTML(fmtId(rating.entity_id))}</td>
      <td><span class="elo-badge ${eloClass(rating.rating)}">${Number(rating.rating).toFixed(1)}</span></td>
      <td>${fmtNum(rating.games_played)}</td>
      <td>${rating.wins}-${rating.losses}-${rating.draws}</td>
    </tr>
    <tr class="arena-history-row" id="arena-history-${escapeAttr(rating.entity_id)}" hidden><td colspan="5"><div class="status-line">Loading history...</div></td></tr>
  `).join('');
  return `
    <section class="card">
      <div class="card-header"><h2>${escapeHTML(title)}</h2></div>
      <div class="card-body">
        ${ratings.length ? `<table class="data-table arena-table"><thead><tr><th>Rank</th><th>ID</th><th>Elo</th><th>Games</th><th>W-L-D</th></tr></thead><tbody>${rows}</tbody></table>` : emptyState('No Ratings Yet', 'Run a tournament to populate this leaderboard.')}
      </div>
    </section>`;
}

window.handleArenaRowKey = function(event, entityId) {
  if (event.key !== 'Enter' && event.key !== ' ') return;
  event.preventDefault();
  toggleArenaHistory(entityId);
};

function eloClass(rating) {
  return rating > 1550 ? 'elo-high' : rating < 1450 ? 'elo-low' : 'elo-mid';
}

window.updateArenaCount = function() {
  const strategies = checkedValues('arena-strategies').length;
  const profiles = checkedValues('arena-profiles').length;
  const rounds = Number(($('#arena-rounds') || {}).value || 1);
  const reps = Number(($('#arena-reps') || {}).value || 1);
  const format = ($('#arena-format') || {}).value || 'swiss';
  const pairings = format === 'round_robin' ? strategies * profiles : Math.min(strategies, profiles);
  const total = pairings * rounds * reps;
  const el = $('#arena-count');
  if (!el) return;
  el.classList.toggle('warning', total > 50);
  el.textContent = `${fmtId(format)}: ${pairings} pairings x ${rounds} rounds x ${reps} reps = ${total} simulations${total > 50 ? '. Large tournaments take longer and cost more.' : ''}`;
};

window.startArenaTournament = async function(event) {
  event.preventDefault();
  clearPoll('arena');
  const panel = $('#arena-job-panel');
  const status = $('#arena-job-status');
  const btn = $('#arena-btn');
  panel.innerHTML = skeleton();
  if (btn) { btn.classList.add('btn-loading'); btn.disabled = true; }
  try {
    const job = await apiPost('/jobs/tournaments', {
      format: $('#arena-format').value,
      rounds: Number($('#arena-rounds').value || 1),
      reps_per_pairing: Number($('#arena-reps').value || 1),
      profile_ids: checkedValues('arena-profiles'),
      strategy_ids: checkedValues('arena-strategies'),
      conversation_model: $('#arena-conversation-model').value,
      judge_model: $('#arena-judge-model').value,
      concurrency: Number($('#arena-concurrency').value || 1),
    });
    status.innerHTML = statusBadge(job.status);
    renderJobPanel(job, panel);
    showToast('Tournament started', 'success');
    window._pollers.arena = setInterval(() => pollJob(job.id, 'arena-job-panel', 'arena-job-status', 'arena'), 900);
  } catch (err) {
    panel.innerHTML = emptyState('Tournament failed', err.message);
    showToast(err.message, 'error');
  } finally {
    if (btn) { btn.classList.remove('btn-loading'); btn.disabled = false; }
  }
};

window.toggleArenaHistory = async function(entityId) {
  const row = $(`#arena-history-${CSS.escape(entityId)}`);
  if (!row) return;
  row.hidden = !row.hidden;
  if (row.hidden || row.dataset.loaded) return;
  try {
    row.innerHTML = '<td colspan="5"><div class="status-line">Loading history…</div></td>';
    const history = await api(`/arena/history/${pathPart(entityId)}`);
    row.dataset.loaded = 'true';
    row.innerHTML = `<td colspan="5">${history.length ? arenaHistoryHTML(history) : '<div class="status-line">No history for this entity.</div>'}</td>`;
  } catch (err) {
    row.innerHTML = `<td colspan="5">${emptyState('Failed to load history', err.message)}</td>`;
  }
};

function arenaHistoryHTML(history) {
  const values = history.map(update => Number(update.rating_after));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const points = values.map((value, index) => {
    const x = history.length === 1 ? 50 : (index / (history.length - 1)) * 100;
    const y = max === min ? 50 : 90 - ((value - min) / (max - min)) * 80;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return `<div class="arena-sparkline" aria-label="Elo rating history sparkline"><svg viewBox="0 0 100 100" preserveAspectRatio="none"><polyline points="${points}" fill="none" stroke="currentColor" stroke-width="3" vector-effect="non-scaling-stroke"/></svg></div><div class="arena-history">${history.map(update => `
    <div class="arena-history-item">
      <span>${Number(update.rating_before).toFixed(1)} → ${Number(update.rating_after).toFixed(1)}</span>
      <span>vs ${escapeHTML(fmtId(update.opponent_id))}</span>
      <span>score ${Number(update.effective_score).toFixed(2)}</span>
    </div>`).join('')}</div>`;
}

// ── Evolution ────────────────────────────────────────────────────

async function renderEvolution() {
  const pool = await api('/evolution/pool');
  const strategies = pool.strategies || [];
  const profiles = pool.profiles || [];
  mainEl.innerHTML = `
    <div class="page-header">
      <h1>Evolution</h1>
      <p>Generated strategy and debtor pools from adversarial tournament feedback.</p>
    </div>
    <div class="grid-2">
      <section class="card">
        <div class="card-header"><h2>Strategy Pool</h2></div>
        <div class="card-body">
          ${strategies.length ? evolutionTable(strategies, 'strategy') : emptyState('No Evolved Strategies', 'Run the evolve command or API to generate candidates.')}
        </div>
      </section>
      <section class="card">
        <div class="card-header"><h2>Debtor Pool</h2></div>
        <div class="card-body">
          ${profiles.length ? evolutionTable(profiles, 'profile') : emptyState('No Hardened Profiles', 'Enable debtor hardening in an evolution cycle to populate this pool.')}
        </div>
      </section>
    </div>`;
}

function evolutionTable(items, type) {
  const rows = items.map(item => {
    const lineage = item.lineage || {};
    const generation = lineage.generation ?? 0;
    const parent = type === 'strategy' ? (lineage.parent_ids || []).join(', ') : lineage.parent_id || '';
    const descriptor = type === 'strategy' ? lineage.mutation_type : lineage.hardening_type;
    return `<tr>
      <td>${escapeHTML(item.id)}</td>
      <td>${generation}</td>
      <td>${escapeHTML(parent || 'seed')}</td>
      <td>${escapeHTML(fmtId(descriptor || 'generated'))}</td>
    </tr>`;
  }).join('');
  return `<table class="data-table"><thead><tr><th>ID</th><th>Generation</th><th>Parent</th><th>Type</th></tr></thead><tbody>${rows}</tbody></table>`;
}

// ── Calibration ──────────────────────────────────────────────────

async function renderCalibration() {
  const [results, variants] = await Promise.all([
    api('/calibration/results'),
    api('/calibration/variants'),
  ]);
  const metrics = Object.entries(results.correlations || {}).map(([metric, value]) => `
    <div class="judgment-score-item">
      <span class="judgment-score-label">${escapeHTML(fmtId(metric))}</span>
      <div class="score-bar-wrap">
        <div class="score-bar"><div class="score-bar-fill" style="width:${Math.max(0, Math.min(1, Number(value) || 0)) * 100}%;background:var(--info)"></div></div>
        <span class="score-bar-label">${Number(value || 0).toFixed(2)} corr</span>
      </div>
    </div>`).join('');
  mainEl.innerHTML = `
    <div class="page-header">
      <h1>Calibration</h1>
      <p>Compare judge scores with human labels and track prompt variants.</p>
    </div>
    <div class="grid-2">
      <section class="card">
        <div class="card-header"><h2>Judge Alignment</h2></div>
        <div class="card-body">
          <div class="overview-strip" style="margin-bottom:var(--space-4)">
            <div class="overview-item"><span class="overview-label">Labels</span><span class="overview-value">${fmtNum(results.label_count || 0)}</span></div>
            <div class="overview-sep" aria-hidden="true"></div>
            <div class="overview-item"><span class="overview-label">Score</span><span class="overview-value">${Number(results.overall_score || 0).toFixed(2)}</span></div>
          </div>
          ${metrics || emptyState('No Labels', 'Upload calibration labels with the API or CLI to compute correlations.')}
        </div>
      </section>
      <section class="card">
        <div class="card-header"><h2>Prompt Variants</h2></div>
        <div class="card-body">
          ${variants.length ? variants.map(v => `<div class="job-summary"><span>${escapeHTML(v.id)}</span><span>score ${Number(v.calibration_score || 0).toFixed(2)}</span></div>`).join('') : emptyState('No Variants', 'Use calibrate --optimize to store a scored judge prompt variant.')}
        </div>
      </section>
    </div>`;
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
