/* ═══════════════════════════════════════════════════════════════
   Collection Swarm — Benchmarks Module
   Model benchmark setup, live probing, polling, report
   rendering with heatmaps, bar charts, and fit distribution.
   Depends on core.js and pages.js.
   ═══════════════════════════════════════════════════════════════ */

// ── Model benchmarks ─────────────────────────────────────────────

async function renderBenchmarks() {
  const [options, jobs, reports] = await Promise.all([
    api('/model-benchmarks/options'),
    api('/jobs'),
    api('/model-benchmarks'),
  ]);
  const defaults = options.defaults || {};
  const selectedModels = options.default_cursor_models || [];
  const modelEntries = (options.cursor_models || []).map(model => [model, model]);
  const roleEntries = (options.roles || []).map(role => [role, fmtId(role)]);
  const profileEntries = (options.profiles || []).map(p => [p.id, fmtId(p.id)]);
  const strategyEntries = (options.strategies || []).map(s => [s.id, fmtId(s.id)]);
  const defaultProfiles = defaults.profile_ids || ['cooperative_hardship'];
  const defaultStrategies = defaults.strategy_ids || ['empathetic_payment_plan'];
  const defaultJudgeProfiles = defaults.judge_profile_ids || ['written_proof_disputer'];
  const benchmarkJobs = jobs.filter(job => job.kind === 'model_benchmark');

  mainEl.innerHTML = `
    <div class="page-header page-header-actions">
      <div>
        <h1>Model Benchmarks</h1>
        <p>Run live Cursor SDK probes for Collector, Debtor, and Judge roles, then inspect recommendations and schema risks.</p>
      </div>
      <button class="btn" type="button" onclick="loadLatestBenchmark()">Load latest result</button>
    </div>

    <section class="benchmark-hero" aria-label="Benchmark recommendation summary">
      <div>
        <p class="eyebrow">Production evaluation</p>
        <h2>Find the model mix that can safely drive Collection Swarm.</h2>
        <p>Collector and Debtor probes measure role-play quality. Judge probes are weighted for parseability because malformed Judgments corrupt saved metrics and playbook rankings.</p>
      </div>
      <div class="benchmark-hero-metrics">
        <div><strong>${fmtNum(modelEntries.length)}</strong><span>Available SDK models</span></div>
        <div><strong>3</strong><span>Production roles</span></div>
        <div><strong>${fmtNum(selectedModels.length * 3)}</strong><span>Default probes</span></div>
      </div>
    </section>

    <div class="grid-2 benchmark-layout">
      <div class="card">
        <div class="card-header"><h2>Benchmark Setup</h2></div>
        <div class="card-body">
          <form class="control-form" onsubmit="startModelBenchmark(event)">
            <div class="form-field">
              <label>Cursor SDK models</label>
              <div class="checkbox-grid benchmark-model-grid">${benchmarkCheckboxList('benchmark-models', modelEntries, selectedModels)}</div>
            </div>
            <div class="form-field">
              <label>Roles</label>
              <div class="checkbox-grid benchmark-role-grid">${benchmarkCheckboxList('benchmark-roles', roleEntries, options.roles || ['collector', 'debtor', 'judge'])}</div>
            </div>
            <div class="form-field">
              <label>Profiles</label>
              <p class="field-summary">Each checked profile is used for Collector and Debtor probes.</p>
              <div class="checkbox-grid" onchange="updateBenchmarkCount()">${benchmarkCheckboxList('benchmark-profiles', profileEntries, defaultProfiles)}</div>
            </div>
            <div class="form-field">
              <label>Strategies</label>
              <p class="field-summary">Each checked strategy is used for Collector probes.</p>
              <div class="checkbox-grid" onchange="updateBenchmarkCount()">${benchmarkCheckboxList('benchmark-strategies', strategyEntries, defaultStrategies)}</div>
            </div>
            <div class="form-field">
              <label>Judge profiles</label>
              <p class="field-summary">Each checked profile is used as the Judge evaluation scenario.</p>
              <div class="checkbox-grid" onchange="updateBenchmarkCount()">${benchmarkCheckboxList('benchmark-judge-profiles', profileEntries, defaultJudgeProfiles)}</div>
            </div>
            ${inputField('benchmark-concurrency', 'Concurrency', defaults.concurrency || 1, 1, 4)}
            <div class="matrix-count" id="benchmark-count" aria-live="polite"></div>
            <div class="btn-row">
              <button class="btn btn-primary" type="submit" id="benchmark-btn">Run benchmark</button>
              <button class="btn" type="button" onclick="selectProductionBenchmarkModels()">Production set</button>
              <button class="btn" type="button" onclick="selectAllBenchmarkModels()">Select all</button>
            </div>
          </form>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><h2>Progress</h2><div id="benchmark-job-status">${statusBadge('queued')}</div></div>
        <div class="card-body" id="benchmark-job-panel">
          ${benchmarkJobs.length ? benchmarkJobs.map(job => benchmarkJobSummaryHTML(job)).join('') : emptyState('Ready', 'Start a benchmark to see live progress and recommendations.')}
        </div>
      </div>
    </div>

    <section class="card benchmark-results-card">
      <div class="card-header"><h2>Results</h2><div id="benchmark-result-status">${reports.length ? statusBadge('completed') : statusBadge('queued')}</div></div>
      <div class="card-body" id="benchmark-results">
        ${reports.length ? benchmarkReportListHTML(reports) : emptyState('No benchmark results', 'Completed benchmark recommendations will appear here.')}
      </div>
    </section>
  `;
  updateBenchmarkCount();
}

window.selectProductionBenchmarkModels = function() {
  const selected = new Set(['composer-2', 'gpt-5.5', 'gpt-5.4', 'gpt-5.3-codex', 'claude-sonnet-4-6', 'claude-opus-4-7', 'gemini-3.1-pro', 'gpt-5.4-mini', 'claude-haiku-4-5']);
  $$('input[name="benchmark-models"]').forEach(input => { input.checked = selected.has(input.value); });
  updateBenchmarkCount();
};

window.selectAllBenchmarkModels = function() {
  $$('input[name="benchmark-models"]').forEach(input => { input.checked = true; });
  updateBenchmarkCount();
};

window.startModelBenchmark = async function(event) {
  event.preventDefault();
  clearPoll('benchmark');
  const panel = $('#benchmark-job-panel');
  const status = $('#benchmark-job-status');
  const btn = $('#benchmark-btn');
  panel.innerHTML = skeleton();
  if (btn) { btn.classList.add('btn-loading'); btn.disabled = true; }
  try {
    const job = await apiPost('/jobs/model-benchmarks', {
      cursor_model_names: checkedValues('benchmark-models'),
      roles: checkedValues('benchmark-roles'),
      profile_ids: checkedValues('benchmark-profiles'),
      strategy_ids: checkedValues('benchmark-strategies'),
      judge_profile_ids: checkedValues('benchmark-judge-profiles'),
      concurrency: Number($('#benchmark-concurrency').value || 1),
    });
    status.innerHTML = statusBadge(job.status);
    renderBenchmarkJobPanel(job, panel);
    showToast('Benchmark started', 'success');
    window._pollers.benchmark = setInterval(() => pollBenchmarkJob(job.id), 1200);
  } catch (err) {
    panel.innerHTML = emptyState('Benchmark failed', err.message);
    showToast(err.message, 'error');
  } finally {
    if (btn) { btn.classList.remove('btn-loading'); btn.disabled = false; }
  }
};

async function pollBenchmarkJob(jobId) {
  try {
    const job = await api(`/jobs/${pathPart(jobId)}`);
    const panel = $('#benchmark-job-panel');
    const status = $('#benchmark-job-status');
    if (status) status.innerHTML = statusBadge(job.status);
    if (panel) renderBenchmarkJobPanel(job, panel);
    if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
      clearPoll('benchmark');
      if (job.benchmark_report) renderBenchmarkReport(job.benchmark_report, job);
      if (job.status === 'completed') showToast('Benchmark completed', 'success');
      if (job.status === 'failed') showToast('Benchmark failed', 'error');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function renderBenchmarkJobPanel(job, panel) {
  const canCancel = job.status === 'queued' || job.status === 'running';
  panel.innerHTML = `
    <div class="status-card">
      <div class="job-item-head">
        <div>
          <div class="mono-id">${escapeHTML(job.id)}</div>
          <div class="status-line">${escapeHTML(job.message || '')}</div>
        </div>
        ${statusBadge(job.status)}
      </div>
      ${progressHTML(job.completed, job.failed, job.total)}
      ${canCancel ? `<button class="btn btn-danger" type="button" onclick="cancelJob(${jsArg(job.id)})">Cancel benchmark</button>` : ''}
      ${job.benchmark_report ? benchmarkRecommendationHTML(job.benchmark_report, job) : ''}
      ${(job.errors || []).length ? `<div class="form-error">${job.errors.map(escapeHTML).join('<br>')}</div>` : ''}
    </div>`;
}

function benchmarkJobSummaryHTML(job) {
  return `
    <button class="job-item" type="button" onclick="showBenchmarkJob(${jsArg(job.id)})">
      <span style="font-size:var(--text-sm)">${escapeHTML(job.id)}</span>
      <span>${statusBadge(job.status)}</span>
      <span style="font-size:var(--text-xs);color:var(--text-secondary)">${job.completed + job.failed} of ${job.total}</span>
    </button>`;
}

window.showBenchmarkJob = async function(jobId) {
  const job = await api(`/jobs/${pathPart(jobId)}`);
  const panel = $('#benchmark-job-panel');
  const status = $('#benchmark-job-status');
  if (status) status.innerHTML = statusBadge(job.status);
  if (panel) renderBenchmarkJobPanel(job, panel);
  if (job.benchmark_report) renderBenchmarkReport(job.benchmark_report, job);
};

window.loadLatestBenchmark = async function() {
  const reports = await api('/model-benchmarks');
  const container = $('#benchmark-results');
  if (!reports.length) {
    if (container) container.innerHTML = emptyState('No benchmark results', 'Run a benchmark first.');
    return;
  }
  const report = await api(`/model-benchmarks/${pathPart(reports[0].job_id)}`);
  renderBenchmarkReport(report, { id: reports[0].job_id, artifacts: {} });
};

function benchmarkReportListHTML(reports) {
  return `
    <div class="benchmark-report-list">
      ${reports.map(report => `
        <button class="job-item" type="button" onclick="loadBenchmarkReport(${jsArg(report.job_id)})">
          <span>${escapeHTML(report.title || 'Benchmark')}</span>
          <span>${statusBadge('completed')}</span>
          <span style="font-size:var(--text-xs);color:var(--text-secondary)">${fmtNum(report.probe_count || 0)} probes · ${relTime(report.generated_at)}</span>
        </button>
      `).join('')}
    </div>`;
}

window.loadBenchmarkReport = async function(jobId) {
  const report = await api(`/model-benchmarks/${pathPart(jobId)}`);
  renderBenchmarkReport(report, { id: jobId, artifacts: {} });
};

function renderBenchmarkReport(report, job = {}) {
  const container = $('#benchmark-results');
  const status = $('#benchmark-result-status');
  if (status) status.innerHTML = statusBadge('completed');
  if (!container) return;

  const recs = report.recommendations || {};
  const assessments = report.assessments || [];
  const probes = report.probes || [];
  const configStatuses = report.config_statuses || [];
  const failed = probes.filter(p => p.status !== 'ok').length;
  const artifacts = job.artifacts || {};
  const roles = ['collector', 'debtor', 'judge'];
  const models = [...new Set(assessments.map(a => a.model_name))].sort();

  container.innerHTML = `
    <div class="bench-dash">
      <div class="bench-dash-strip">
        ${roles.map(role => `
          <div class="bench-dash-rec">
            <span class="bench-dash-rec-label">${escapeHTML(fmtId(role))}</span>
            <span class="bench-dash-rec-value">${escapeHTML(recs[role] || 'n/a')}</span>
          </div>`).join('')}
        <div class="bench-dash-stat">
          <span class="bench-dash-stat-value">${fmtNum(probes.length)}</span>
          <span class="bench-dash-stat-label">probes</span>
        </div>
        <div class="bench-dash-stat">
          <span class="bench-dash-stat-value ${failed ? 'score-bad' : 'score-good'}">${fmtNum(failed)}</span>
          <span class="bench-dash-stat-label">failed</span>
        </div>
        <div class="bench-dash-stat">
          <span class="bench-dash-stat-value">${escapeHTML(relTime(report.generated_at))}</span>
          <span class="bench-dash-stat-label">generated</span>
        </div>
      </div>

      <div class="bench-tabs" role="tablist" aria-label="Benchmark views">
        <button class="tab-btn active" role="tab" aria-selected="true" onclick="switchBenchTab(this, 'bench-tab-overview')">Overview</button>
        ${roles.map(role => `<button class="tab-btn" role="tab" aria-selected="false" onclick="switchBenchTab(this, 'bench-tab-${role}')">${escapeHTML(fmtId(role))}</button>`).join('')}
        <button class="tab-btn" role="tab" aria-selected="false" onclick="switchBenchTab(this, 'bench-tab-health')">Config Health</button>
      </div>

      <div id="bench-tab-overview" class="bench-tab-panel active">
        ${benchHeatmapHTML(assessments, models, roles)}
        <div class="bench-grid-2">
          ${benchBarChartHTML(assessments, models, roles)}
          ${benchFitDistHTML(assessments, roles)}
        </div>
      </div>

      ${roles.map(role => `
        <div id="bench-tab-${role}" class="bench-tab-panel">
          ${benchRoleDetailHTML(report, role, recs[role])}
        </div>`).join('')}

      <div id="bench-tab-health" class="bench-tab-panel">
        ${benchConfigHealthHTML(configStatuses)}
      </div>

      ${artifacts.markdown || artifacts.json ? `
        <div class="bench-dash-artifacts">
          ${artifacts.markdown ? `<span>Markdown: <code>${escapeHTML(artifacts.markdown)}</code></span>` : ''}
          ${artifacts.json ? `<span>JSON: <code>${escapeHTML(artifacts.json)}</code></span>` : ''}
        </div>` : ''}
    </div>`;
}

window.switchBenchTab = function(btn, panelId) {
  const tabs = btn.closest('.bench-tabs');
  const dash = btn.closest('.bench-dash');
  $$('.tab-btn', tabs).forEach(b => { b.classList.remove('active'); b.setAttribute('aria-selected', 'false'); });
  btn.classList.add('active');
  btn.setAttribute('aria-selected', 'true');
  $$('.bench-tab-panel', dash).forEach(p => p.classList.remove('active'));
  const panel = $(`#${panelId}`, dash);
  if (panel) panel.classList.add('active');
};

function benchHeatmapHTML(assessments, models, roles) {
  const lookup = {};
  for (const a of assessments) {
    const key = `${a.model_name}::${a.role}`;
    if (!lookup[key]) lookup[key] = [];
    lookup[key].push(a.score);
  }
  function avg(key) {
    const scores = lookup[key];
    if (!scores || !scores.length) return null;
    return scores.reduce((a, b) => a + b, 0) / scores.length;
  }
  function heatColor(score) {
    if (score === null) return 'var(--bg-elevated)';
    if (score >= 9) return 'var(--success)';
    if (score >= 7) return 'oklch(68% 0.14 155)';
    if (score >= 5) return 'var(--warning)';
    if (score >= 3) return 'oklch(68% 0.14 55)';
    return 'var(--danger)';
  }
  function textColor(score) {
    if (score === null) return 'var(--text-tertiary)';
    return score >= 5 ? 'oklch(15% 0 0)' : 'oklch(95% 0 0)';
  }

  return `
    <div class="bench-heatmap-wrap">
      <h3>Score Heatmap</h3>
      <p class="bench-section-desc">Average score per model and role across all scenarios. Higher is better.</p>
      <div class="bench-heatmap" style="grid-template-columns: minmax(120px, auto) repeat(${roles.length}, 1fr)">
        <div class="bench-hm-corner"></div>
        ${roles.map(r => `<div class="bench-hm-colhead">${escapeHTML(fmtId(r))}</div>`).join('')}
        ${models.map(model => `
          <div class="bench-hm-rowhead">${escapeHTML(model)}</div>
          ${roles.map(role => {
            const score = avg(`${model}::${role}`);
            const display = score !== null ? score.toFixed(1) : '\u2014';
            return `<div class="bench-hm-cell" style="background:${heatColor(score)};color:${textColor(score)}" title="${escapeAttr(model)} / ${escapeAttr(fmtId(role))}: ${display}/10">${display}</div>`;
          }).join('')}
        `).join('')}
      </div>
      <div class="bench-hm-legend">
        <span style="background:var(--danger)"></span><span>1-2</span>
        <span style="background:oklch(68% 0.14 55)"></span><span>3-4</span>
        <span style="background:var(--warning)"></span><span>5-6</span>
        <span style="background:oklch(68% 0.14 155)"></span><span>7-8</span>
        <span style="background:var(--success)"></span><span>9-10</span>
      </div>
    </div>`;
}

function benchBarChartHTML(assessments, models, roles) {
  const lookup = {};
  for (const a of assessments) {
    const key = `${a.model_name}::${a.role}`;
    if (!lookup[key]) lookup[key] = [];
    lookup[key].push(a.score);
  }
  function avgScore(model, role) {
    const scores = lookup[`${model}::${role}`];
    if (!scores || !scores.length) return 0;
    return scores.reduce((a, b) => a + b, 0) / scores.length;
  }
  const roleColors = { collector: 'var(--accent-primary)', debtor: 'oklch(65% 0.17 310)', judge: 'var(--warning)' };

  return `
    <div class="bench-barchart-wrap">
      <h3>Score Comparison</h3>
      <p class="bench-section-desc">Average score per model, grouped by role.</p>
      <div class="bench-barchart-legend">
        ${roles.map(r => `<span><i style="background:${roleColors[r]}"></i>${escapeHTML(fmtId(r))}</span>`).join('')}
      </div>
      <div class="bench-barchart">
        ${models.map(model => `
          <div class="bench-bar-group">
            <span class="bench-bar-label">${escapeHTML(model)}</span>
            <div class="bench-bar-tracks">
              ${roles.map(role => {
                const score = avgScore(model, role);
                const w = Math.max(score * 10, 2);
                return `<div class="bench-bar-track"><div class="bench-bar-fill" style="width:${w}%;background:${roleColors[role]}" title="${escapeAttr(fmtId(role))}: ${score.toFixed(1)}/10"></div><span class="bench-bar-val">${score.toFixed(1)}</span></div>`;
              }).join('')}
            </div>
          </div>`).join('')}
      </div>
    </div>`;
}

function benchFitDistHTML(assessments, roles) {
  const fitOrder = ['Primary recommendation', 'Strong candidate', 'Usable with caution', 'Unsafe without parser hardening', 'Unavailable'];
  const fitColors = {
    'Primary recommendation': 'var(--success)',
    'Strong candidate': 'oklch(68% 0.14 155)',
    'Usable with caution': 'var(--warning)',
    'Unsafe without parser hardening': 'oklch(68% 0.14 55)',
    'Unavailable': 'var(--danger)',
  };
  const fitShort = {
    'Primary recommendation': 'Primary',
    'Strong candidate': 'Strong',
    'Usable with caution': 'Caution',
    'Unsafe without parser hardening': 'Unsafe',
    'Unavailable': 'Unavailable',
  };

  return `
    <div class="bench-fitdist-wrap">
      <h3>Fit Distribution</h3>
      <p class="bench-section-desc">How models were classified per role.</p>
      ${roles.map(role => {
        const roleAssess = assessments.filter(a => a.role === role);
        const total = roleAssess.length || 1;
        const counts = {};
        for (const a of roleAssess) counts[a.fit] = (counts[a.fit] || 0) + 1;
        return `
          <div class="bench-fitdist-role">
            <span class="bench-fitdist-role-label">${escapeHTML(fmtId(role))}</span>
            <div class="bench-fitdist-bar">
              ${fitOrder.filter(f => counts[f]).map(f => {
                const pctW = (counts[f] / total) * 100;
                return `<div class="bench-fitdist-seg" style="width:${Math.max(pctW, 4)}%;background:${fitColors[f]}" title="${escapeAttr(f)}: ${counts[f]}"><span>${counts[f]}</span></div>`;
              }).join('')}
            </div>
          </div>`;
      }).join('')}
      <div class="bench-fitdist-legend">
        ${fitOrder.map(f => `<span><i style="background:${fitColors[f]}"></i>${escapeHTML(fitShort[f])}</span>`).join('')}
      </div>
    </div>`;
}

function benchRoleDetailHTML(report, role, recommended) {
  const rows = (report.assessments || [])
    .filter(item => item.role === role)
    .sort((a, b) => (b.score - a.score) || a.model_name.localeCompare(b.model_name));
  const avgScore = rows.length ? (rows.reduce((s, r) => s + r.score, 0) / rows.length).toFixed(1) : '0';
  const bestScore = rows.length ? Math.max(...rows.map(r => r.score)) : 0;
  const worstScore = rows.length ? Math.min(...rows.map(r => r.score)) : 0;

  return `
    <div class="bench-role-detail">
      <div class="bench-role-kpis">
        <div class="bench-role-kpi"><span class="bench-role-kpi-val">${escapeHTML(recommended || 'n/a')}</span><span class="bench-role-kpi-label">Recommended</span></div>
        <div class="bench-role-kpi"><span class="bench-role-kpi-val">${avgScore}</span><span class="bench-role-kpi-label">Avg score</span></div>
        <div class="bench-role-kpi"><span class="bench-role-kpi-val score-good">${bestScore}/10</span><span class="bench-role-kpi-label">Best</span></div>
        <div class="bench-role-kpi"><span class="bench-role-kpi-val ${benchmarkScoreClass(worstScore)}">${worstScore}/10</span><span class="bench-role-kpi-label">Worst</span></div>
      </div>

      <div class="bench-role-bars">
        ${rows.map(row => {
          const w = Math.max(row.score * 10, 2);
          const isRec = row.model_name === recommended;
          return `
            <div class="bench-role-bar-row ${isRec ? 'is-rec' : ''}">
              <span class="bench-role-bar-model">${escapeHTML(row.model_name)}${isRec ? ' <em>rec</em>' : ''}</span>
              <div class="bench-role-bar-track">
                <div class="bench-role-bar-fill ${benchmarkScoreClass(row.score)}" style="width:${w}%"></div>
              </div>
              <span class="bench-role-bar-score ${benchmarkScoreClass(row.score)}">${row.score}/10</span>
            </div>`;
        }).join('')}
      </div>

      <div class="bench-table-wrap">
        <table class="data-table benchmark-table">
          <thead><tr><th>Model</th><th>Score</th><th>Fit</th><th>Evidence</th><th>Caution</th></tr></thead>
          <tbody>
            ${rows.map(row => `
              <tr class="${row.model_name === recommended ? 'bench-rec-row' : ''}">
                <td>${escapeHTML(row.model_name)}</td>
                <td><span class="benchmark-score ${benchmarkScoreClass(row.score)}">${escapeHTML(row.score)}/10</span></td>
                <td><span class="bench-fit-badge ${benchFitClass(row.fit)}">${escapeHTML(row.fit)}</span></td>
                <td>${escapeHTML(row.evidence)}</td>
                <td>${escapeHTML(row.caution)}</td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>`;
}

function benchConfigHealthHTML(statuses) {
  if (!statuses || !statuses.length) return emptyState('No config data', 'No configuration health data available.');
  const works = statuses.filter(s => s.live_status === 'works').length;
  const fails = statuses.filter(s => s.live_status === 'fails').length;
  return `
    <div class="bench-health">
      <div class="bench-health-strip">
        <div class="bench-health-stat"><span class="bench-health-val score-good">${works}</span><span>Working</span></div>
        <div class="bench-health-stat"><span class="bench-health-val ${fails ? 'score-bad' : 'score-good'}">${fails}</span><span>Failing</span></div>
        <div class="bench-health-stat"><span class="bench-health-val">${statuses.length}</span><span>Configured</span></div>
      </div>
      <table class="data-table">
        <thead><tr><th>Config ID</th><th>Model</th><th>Status</th><th>Action</th></tr></thead>
        <tbody>
          ${statuses.map(s => `
            <tr>
              <td><code>${escapeHTML(s.configured_id)}</code></td>
              <td>${escapeHTML(s.model_name)}</td>
              <td><span class="badge ${s.live_status === 'works' ? 'badge-success' : 'badge-danger'}">${escapeHTML(s.live_status)}</span></td>
              <td>${escapeHTML(s.action)}</td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
}

function benchFitClass(fit) {
  if (fit === 'Primary recommendation') return 'fit-primary';
  if (fit === 'Strong candidate') return 'fit-strong';
  if (fit === 'Usable with caution') return 'fit-caution';
  if (fit === 'Unsafe without parser hardening') return 'fit-unsafe';
  return 'fit-unavailable';
}

function benchmarkRecommendationHTML(report, job = {}) {
  return '';
}

function benchmarkScoreClass(score) {
  score = Number(score) || 0;
  if (score >= 9) return 'score-good';
  if (score >= 6) return 'score-mid';
  return 'score-bad';
}

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
