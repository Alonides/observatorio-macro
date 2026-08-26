const fmt = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 2 });
const dateFmt = new Intl.DateTimeFormat('es-ES', { day: '2-digit', month: 'short', year: 'numeric' });
const monitorState = { latest: null, history: null, range: 365 };
const COLORS = { gold: '#d4b568', blue: '#76a9e5', green: '#58c990', red: '#ed776e', violet: '#b993e8' };

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  })[char]);
}

function number(value, digits = 2) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toLocaleString('es-ES', { maximumFractionDigits: digits, minimumFractionDigits: digits }) : '—';
}

function nested(object, path) {
  return path.reduce((value, key) => value && typeof value === 'object' ? value[key] : undefined, object);
}

function renderHealth(data) {
  const health = document.querySelector('#monitor-health');
  const generated = data.generated_at ? new Date(data.generated_at).toLocaleString('es-ES', {
    timeZone: 'Europe/Oslo', dateStyle: 'medium', timeStyle: 'short',
  }) : 'pendiente';
  const quality = nested(data, ['current', 'operational', 'data_quality']) || 'pending';
  health.className = `health status-${quality === 'complete' ? 'ok' : 'operational_partial'}`;
  health.innerHTML = `<strong>Modelo ${escapeHtml(data.model_version || '—')}</strong><span>${escapeHtml(data.asof || 'sin fecha')} · ${escapeHtml(generated)}</span>`;
}

function renderAlert(data) {
  const alert = data.alert || { level: 'pending', label: 'Pendiente' };
  const card = document.querySelector('#alert-card');
  card.className = `card alert-card ${escapeHtml(alert.level || 'pending')}`;
  document.querySelector('#alert-label').textContent = alert.label || 'Pendiente';
  const blocks = nested(data, ['current', 'operational', 'blocks']) || {};
  const scores = Object.values(blocks).map(block => Number(block.score)).filter(Number.isFinite);
  document.querySelector('#alert-score').textContent = scores.length ? number(Math.max(...scores), 0) : '—';
  document.querySelector('#headline').textContent = data.headline || 'Sin informe disponible';
  document.querySelector('#summary').textContent = data.summary || 'El agente todavía no ha generado una lectura.';
  document.querySelector('#reasons').innerHTML = (data.reasons || []).map(reason => `<span>${escapeHtml(reason)}</span>`).join('');
}

function renderSchedule(data) {
  const schedule = data.schedule || {};
  const rows = [
    ['Monitor intermedio', schedule.daily_monitor],
    ['Informe completo', schedule.weekly_report],
    ['Hora Oslo', schedule.oslo_note],
    ['Entrega', schedule.delivery],
  ];
  document.querySelector('#schedule').innerHTML = rows.map(([label, value]) => `
    <div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value || '—')}</dd></div>`).join('');
}

function severity(block) {
  const score = Number(block.score || 0);
  if (block.state === 'confirmed' || block.state === 'rejection_regime' || score >= 80) return 'critical';
  if (block.state === 'us_discrimination' || score >= 65) return 'alert';
  if (block.state === 'rejection_pulse' || score >= 35) return 'watch';
  return 'normal';
}

function renderBlocks(data) {
  const blocks = nested(data, ['current', 'operational', 'blocks']) || {};
  document.querySelector('#block-grid').innerHTML = ['URP', 'URR', 'DSS', 'NKS', 'NRS'].map(key => {
    const block = blocks[key] || { label: key, score: 0, state: 'sin_datos', coverage: 0 };
    return `<article class="monitor-block ${severity(block)}">
      <div class="block-code">${escapeHtml(key)}</div>
      <div class="block-score">${number(block.score, 0)}</div>
      <h3>${escapeHtml(block.label || key)}</h3>
      <p>${escapeHtml(block.state || 'sin_datos')} · cobertura ${number((Number(block.coverage) || 0) * 100, 0)} %</p>
    </article>`;
  }).join('');
}

function renderKeyValues(data) {
  const current = data.current || {};
  const values = [
    ['UST 30a · 10 sesiones', nested(current, ['urp', 'values', 'ust30_change_10_bp']), ' pb'],
    ['Dólar amplio · caída', nested(current, ['urp', 'values', 'broad_usd_drop_10_pct']), ' %'],
    ['VIX', nested(current, ['urp', 'values', 'vix']), ''],
    ['EUR/NOK · 20 sesiones', nested(current, ['nks', 'values', 'eurnok_change_20_pct']), ' %'],
    ['NOK débil vs SEK', nested(current, ['nks', 'values', 'noksek_change_20_pct']), ' %'],
    ['Residual NOK', nested(current, ['nks', 'values', 'nok_residual_z20']), 'σ'],
    ['Norway–Bund · 20 sesiones', nested(current, ['nks', 'values', 'norway_bund_change_20_bp']), ' pb'],
    ['NRS · puertas cumplidas', nested(current, ['nrs', 'gate_score']), ' %'],
  ];
  document.querySelector('#key-values').innerHTML = values.map(([label, value, suffix]) => `
    <div class="key-value"><strong>${number(value)}${Number.isFinite(Number(value)) ? suffix : ''}</strong><span>${escapeHtml(label)}</span></div>`).join('');
}

function renderDeltas(data) {
  const deltas = data.score_deltas_5_sessions || {};
  document.querySelector('#deltas').innerHTML = ['URP', 'URR', 'DSS', 'NKS', 'NRS'].map(key => {
    const value = Number(deltas[key] || 0);
    const klass = value > 0.01 ? 'up' : value < -0.01 ? 'down' : '';
    return `<div class="delta ${klass}"><strong>${value >= 0 ? '+' : ''}${number(value)}</strong><span>${escapeHtml(key)}</span></div>`;
  }).join('');
}

function renderReport(data) {
  document.querySelector('#report-date').textContent = `Informe a ${data.asof ? dateFmt.format(new Date(`${data.asof}T00:00:00Z`)) : 'fecha pendiente'}`;
  document.querySelector('#report-mode').textContent = data.mode === 'weekly' ? 'Semanal' : 'Monitor diario';
  const reasons = (data.reasons || []).map(reason => `<li>${escapeHtml(reason)}</li>`).join('');
  document.querySelector('#report-summary').innerHTML = `
    <p><strong>${escapeHtml(data.headline || '')}</strong></p>
    <p>${escapeHtml(data.summary || '')}</p>
    ${reasons ? `<ul>${reasons}</ul>` : ''}`;
  const coverage = nested(data, ['current', 'operational', 'missing_confirmations']) || [];
  const residual = data.source_status || {};
  document.querySelector('#method-content').innerHTML = `
    <p>Modelo operativo v1.0 sobre núcleo v0.4.1. Las reglas son deterministas, versionadas y no alteran los scores validados.</p>
    <p>Residual disponible: ${escapeHtml(String(residual.residual_points ?? '—'))} observaciones, ${escapeHtml(residual.residual_start || '—')} → ${escapeHtml(residual.residual_end || '—')}.</p>
    <p>Confirmaciones ausentes: ${coverage.length ? coverage.map(escapeHtml).join(', ') : 'ninguna en la lectura actual'}.</p>
    <p>La ausencia de señal no demuestra que no exista riesgo estructural; sólo indica que la configuración definida no está activa.</p>`;
}

function cleanSeries(id) {
  const raw = nested(monitorState, ['history', 'series', id]) || [];
  const points = raw.map(point => ({
    date: point.date,
    time: Date.parse(`${point.date}T00:00:00Z`),
    value: Number(point.value),
  })).filter(point => Number.isFinite(point.time) && Number.isFinite(point.value)).sort((a, b) => a.time - b.time);
  if (monitorState.range === 'all' || !points.length) return points;
  const cutoff = points[points.length - 1].time - Number(monitorState.range) * 86400000;
  return points.filter(point => point.time >= cutoff);
}

function lineChart(selector, definitions, normalized = false, zeroLine = false) {
  const container = document.querySelector(selector);
  const datasets = definitions.map(def => ({ ...def, points: cleanSeries(def.id) })).filter(def => def.points.length > 1);
  if (!datasets.length) {
    container.innerHTML = '<p class="chart-empty">Aún no hay historia suficiente.</p>';
    return;
  }
  const width = 820, height = 286, margin = { top: 24, right: 18, bottom: 34, left: 52 };
  datasets.forEach(dataset => {
    const base = dataset.points[0].value;
    dataset.display = dataset.points.map(point => ({ ...point, plotted: normalized && base ? point.value / base * 100 : point.value }));
  });
  const values = datasets.flatMap(dataset => dataset.display.map(point => point.plotted));
  const times = datasets.flatMap(dataset => dataset.display.map(point => point.time));
  if (zeroLine) values.push(0);
  let yMin = Math.min(...values), yMax = Math.max(...values);
  const pad = yMax === yMin ? 1 : (yMax - yMin) * .12;
  yMin -= pad; yMax += pad;
  const xMin = Math.min(...times), xMax = Math.max(...times);
  const x = time => margin.left + (time - xMin) / Math.max(xMax - xMin, 1) * (width - margin.left - margin.right);
  const y = value => margin.top + (yMax - value) / Math.max(yMax - yMin, 1) * (height - margin.top - margin.bottom);
  const grid = Array.from({ length: 5 }, (_, index) => {
    const value = yMin + (yMax - yMin) * index / 4;
    return `<line x1="${margin.left}" x2="${width - margin.right}" y1="${y(value)}" y2="${y(value)}" class="grid-line" />
      <text x="${margin.left - 8}" y="${y(value) + 4}" text-anchor="end" class="axis-label">${number(value, 1)}</text>`;
  }).join('');
  const zero = zeroLine && yMin < 0 && yMax > 0 ? `<line x1="${margin.left}" x2="${width - margin.right}" y1="${y(0)}" y2="${y(0)}" class="zero-line" />` : '';
  const paths = datasets.map(dataset => {
    const path = dataset.display.map((point, index) => `${index ? 'L' : 'M'}${x(point.time).toFixed(1)},${y(point.plotted).toFixed(1)}`).join(' ');
    return `<path d="${path}" fill="none" stroke="${dataset.color}" stroke-width="2.4" vector-effect="non-scaling-stroke" />`;
  }).join('');
  const legend = datasets.map(dataset => {
    const last = dataset.display[dataset.display.length - 1];
    return `<span><i style="background:${dataset.color}"></i>${escapeHtml(dataset.label)} <strong>${number(last.plotted)}</strong></span>`;
  }).join('');
  container.innerHTML = `<div class="chart-legend">${legend}</div><svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">${grid}${zero}${paths}</svg>`;
}

function renderCharts() {
  lineChart('#fx-chart', [
    { id: 'EURNOK', label: 'EUR/NOK', color: COLORS.red },
    { id: 'NOKSEK', label: 'NOK/SEK', color: COLORS.blue },
  ], true, false);
  lineChart('#residual-chart', [
    { id: 'NOK_RESIDUAL_Z20', label: 'Residual z20', color: COLORS.gold },
  ], false, true);
}

function renderAll() {
  const data = monitorState.latest;
  renderHealth(data);
  renderAlert(data);
  renderSchedule(data);
  renderBlocks(data);
  renderKeyValues(data);
  renderDeltas(data);
  renderReport(data);
  renderCharts();
}

async function loadJson(path) {
  const response = await fetch(path, { cache: 'no-store' });
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

document.querySelectorAll('[data-monitor-range]').forEach(button => button.addEventListener('click', () => {
  monitorState.range = button.dataset.monitorRange === 'all' ? 'all' : Number(button.dataset.monitorRange);
  document.querySelectorAll('[data-monitor-range]').forEach(item => item.classList.toggle('selected', item === button));
  renderCharts();
}));

Promise.all([
  loadJson('data/debt_nok/latest.json'),
  loadJson('data/debt_nok/history.json'),
]).then(([latest, history]) => {
  monitorState.latest = latest;
  monitorState.history = history;
  renderAll();
}).catch(error => {
  document.querySelector('#monitor-health').textContent = 'Error de carga';
  document.querySelector('#alert-card').innerHTML = `<div class="monitor-error"><strong>No se pudo cargar el monitor.</strong><br>${escapeHtml(error.message)}</div>`;
});
