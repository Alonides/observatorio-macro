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

function displayDate(raw) {
  return raw ? dateFmt.format(new Date(`${raw}T00:00:00Z`)) : '—';
}

function lagText(raw) {
  const lag = Number(raw);
  if (!Number.isFinite(lag)) return 'sin fecha';
  if (lag <= 0) return 'al día';
  if (lag === 1) return '1 día hábil';
  return `${lag} días hábiles`;
}

function renderHealth(data) {
  const health = document.querySelector('#monitor-health');
  const generated = data.generated_at ? new Date(data.generated_at).toLocaleString('es-ES', {
    timeZone: 'Europe/Oslo', dateStyle: 'medium', timeStyle: 'short',
  }) : 'pendiente';
  const coverage = nested(data, ['current', 'operational', 'data_quality']) || 'pending';
  const freshness = nested(data, ['freshness', 'quality']) || 'unavailable';
  const healthy = coverage === 'complete' && ['fresh', 'delayed'].includes(freshness);
  health.className = `health status-${healthy ? 'ok' : 'operational_partial'}`;
  health.innerHTML = `<strong>Modelo ${escapeHtml(data.model_version || '—')}</strong><span>Informe ${escapeHtml(data.report_date || 'sin fecha')} · último oficial ${escapeHtml(nested(data, ['freshness', 'latest_input_date']) || data.asof || '—')} · ${escapeHtml(generated)}</span>`;
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
  document.querySelector('#summary').textContent = data.summary || 'El agente todavía no ha generado una lectura oficial.';
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

function severity(block, key) {
  const score = Number(block.score || 0);
  if (block.state === 'rejection_regime' || (key === 'NKS' && score >= 80)) return 'critical';
  if (block.state === 'confirmed' || block.state === 'us_discrimination' || score >= 65) return 'alert';
  if (block.state === 'rejection_pulse' || score >= 35) return 'watch';
  return 'normal';
}

function renderBlocks(data) {
  const blocks = nested(data, ['current', 'operational', 'blocks']) || {};
  document.querySelector('#block-grid').innerHTML = ['URP', 'URR', 'DSS', 'NKS', 'NRS'].map(key => {
    const block = blocks[key] || { label: key, score: 0, state: 'sin_datos', coverage: 0 };
    const lag = lagText(block.business_day_lag);
    return `<article class="monitor-block ${severity(block, key)}">
      <div class="block-code">${escapeHtml(key)}</div>
      <div class="block-score">${number(block.score, 0)}</div>
      <h3>${escapeHtml(block.label || key)}</h3>
      <p>${escapeHtml(block.state || 'sin_datos')} · cobertura ${number((Number(block.coverage) || 0) * 100, 0)} %</p>
      <p>Datos ${escapeHtml(block.asof || '—')} · ${escapeHtml(lag)} · ${escapeHtml(block.freshness_label || 'No disponible')}</p>
    </article>`;
  }).join('');
}

function renderFastLane(data) {
  const section = document.querySelector('#fast-lane-section');
  const fast = data.fast_lane || {};
  const status = fast.status || 'unavailable';
  section.className = `card fast-lane-card ${escapeHtml(status)}${fast.review_required ? ' review-required' : ''}`;
  document.querySelector('#fast-lane-title').textContent = fast.label || 'Vía rápida no disponible';
  document.querySelector('#fast-lane-label').textContent = fast.review_required ? 'Revisión humana' : 'Provisional';
  document.querySelector('#fast-lane-message').textContent = fast.message || 'No hay una extensión provisional validada más reciente que la lectura oficial.';
  document.querySelector('#fast-lane-disclaimer').textContent = fast.disclaimer || 'La lectura oficial conserva prioridad.';

  const comparisons = fast.comparisons || {};
  document.querySelector('#fast-lane-comparison').innerHTML = ['URP', 'URR', 'DSS', 'NKS', 'NRS'].map(key => {
    const item = comparisons[key] || {};
    const delta = Number(item.delta);
    const deltaClass = Number.isFinite(delta) && delta > 0.01 ? 'up' : Number.isFinite(delta) && delta < -0.01 ? 'down' : '';
    return `<article class="fast-comparison ${deltaClass}">
      <div class="block-code">${escapeHtml(key)}</div>
      <div class="fast-score-pair"><span>${number(item.official_score, 0)}</span><b>→</b><strong>${number(item.provisional_score, 0)}</strong></div>
      <p>${escapeHtml(item.provisional_state || 'sin extensión')} · Δ ${Number.isFinite(delta) && delta >= 0 ? '+' : ''}${number(delta)}</p>
      <p>Datos provisionales ${escapeHtml(item.provisional_asof || '—')}</p>
    </article>`;
  }).join('');

  const bridge = fast.bridge || {};
  const targets = bridge.targets || {};
  const visible = Object.entries(targets).filter(([, item]) => item && !['not_needed', 'unavailable'].includes(item.status));
  const rows = visible.map(([key, item]) => {
    const validation = item.validation || {};
    return `<tr><td>${escapeHtml(key)}</td><td>${escapeHtml(item.status || '—')}</td><td>${escapeHtml(item.official_last || '—')}</td><td>${escapeHtml(item.proxy_last || '—')}</td><td>${escapeHtml(item.bridge_end || '—')}</td><td>${number(validation.correlation, 3)}</td><td>${number(validation.mae_pct_points, 3)} pp</td></tr>`;
  }).join('');
  const errors = Object.entries(bridge.errors || {}).map(([key, value]) => `<li><strong>${escapeHtml(key)}:</strong> ${escapeHtml(value)}</li>`).join('');
  const active = (bridge.active_targets || []).map(escapeHtml).join(', ') || 'ninguno';
  document.querySelector('#fast-bridge-content').innerHTML = `
    <p>Estado del puente: <strong>${escapeHtml(bridge.status || 'no disponible')}</strong>. Objetivos activos: ${active}.</p>
    ${rows ? `<table><thead><tr><th>Serie</th><th>Estado</th><th>Oficial</th><th>Proxy</th><th>Extensión</th><th>Corr.</th><th>Error</th></tr></thead><tbody>${rows}</tbody></table>` : '<p>No hay puentes activos o rechazados que mostrar.</p>'}
    ${errors ? `<p>Fuentes rápidas no disponibles:</p><ul>${errors}</ul>` : ''}
    <p>${escapeHtml(bridge.method || 'Los proxies nunca sustituyen la historia oficial.')}</p>`;
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

function freshnessTable(data) {
  const blocks = nested(data, ['freshness', 'blocks']) || {};
  const rows = ['URP', 'URR', 'DSS', 'NKS', 'NRS'].map(key => {
    const item = blocks[key] || {};
    return `<tr><td>${escapeHtml(key)}</td><td>${escapeHtml(item.asof || '—')}</td><td>${escapeHtml(lagText(item.business_day_lag))}</td><td>${escapeHtml(item.label || 'No disponible')}</td></tr>`;
  }).join('');
  return `<table><thead><tr><th>Bloque</th><th>Datos a</th><th>Retraso</th><th>Frescura</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderReport(data) {
  document.querySelector('#report-date').textContent = `Informe de ${data.report_date ? displayDate(data.report_date) : 'fecha pendiente'}`;
  document.querySelector('#report-mode').textContent = data.mode === 'weekly' ? 'Semanal' : 'Monitor diario';
  const reasons = (data.reasons || []).map(reason => `<li>${escapeHtml(reason)}</li>`).join('');
  const freshness = data.freshness || {};
  document.querySelector('#report-summary').innerHTML = `
    <p><strong>Lectura oficial: ${escapeHtml(data.headline || '')}</strong></p>
    <p>${escapeHtml(data.summary || '')}</p>
    <p>Último dato oficial: <strong>${escapeHtml(freshness.latest_input_date || data.asof || '—')}</strong>. Bloque oficial más retrasado: <strong>${escapeHtml(freshness.oldest_block || '—')}</strong> (${escapeHtml(lagText(freshness.maximum_business_day_lag))}).</p>
    ${reasons ? `<ul>${reasons}</ul>` : ''}`;
  const coverage = nested(data, ['current', 'operational', 'missing_confirmations']) || [];
  const sources = data.source_status || {};
  const fast = data.fast_lane || {};
  document.querySelector('#method-content').innerHTML = `
    <p>Modelo operativo ${escapeHtml(data.model_version || '—')} sobre núcleo v0.4.1. La lectura oficial es determinista, versionada y autoritativa.</p>
    ${freshnessTable(data)}
    <p>Residual oficial: ${escapeHtml(String(sources.official_residual_points ?? '—'))} observaciones, ${escapeHtml(sources.official_residual_start || '—')} → ${escapeHtml(sources.official_residual_end || '—')}.</p>
    <p>Residual provisional: ${escapeHtml(String(sources.fast_residual_points ?? '—'))} observaciones, ${escapeHtml(sources.fast_residual_start || '—')} → ${escapeHtml(sources.fast_residual_end || '—')}.</p>
    <p>Confirmaciones oficiales ausentes: ${coverage.length ? coverage.map(escapeHtml).join(', ') : 'ninguna en la lectura actual'}.</p>
    <p>La vía rápida está marcada como <strong>${escapeHtml(fast.status || 'no disponible')}</strong>; utiliza proxies oficiales de vida corta, no sobrescribe observaciones y no confirma por sí sola un cambio de régimen.</p>
    <p>Cada bloque oficial conserva su última lectura completa y declara su fecha. La ausencia de señal no demuestra que no exista riesgo estructural.</p>`;
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
  renderFastLane(data);
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
