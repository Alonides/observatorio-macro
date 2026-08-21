const fmt = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 2 });
const compactFmt = new Intl.NumberFormat('es-ES', { notation: 'compact', maximumFractionDigits: 1 });
const dateFmt = new Intl.DateTimeFormat('es-ES', { day: '2-digit', month: 'short', year: '2-digit' });
const state = { latest: null, history: null, range: 365 };

const COLORS = {
  gold: '#d4b568', blue: '#76a9e5', green: '#58c990', red: '#ed776e',
  violet: '#b993e8', cyan: '#68c7cf', orange: '#e69a62', silver: '#b7c5c0',
};

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  })[char]);
}

function valueText(value, unit = '') {
  return value == null ? '—' : `${fmt.format(value)} ${unit}`.trim();
}

function safeSource(url, label) {
  if (!String(url || '').startsWith('https://')) return escapeHtml(label || '—');
  return `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(label || 'Fuente')}</a>`;
}

function signalClass(active) {
  return active === true ? 'active' : active === false ? 'inactive' : 'unknown';
}

function signalValue(signal) {
  if (signal.value == null) return '—';
  if (signal.key === 'dollar') return `${fmt.format(signal.value)} %`;
  if (['real_yield', 'breakeven', 'repo', 'global_duration', 'us_specific'].includes(signal.key)) {
    return `${fmt.format(signal.value * 100)} pb`;
  }
  return fmt.format(signal.value);
}

function renderHealth(data) {
  const generated = data.generated_at
    ? new Date(data.generated_at).toLocaleString('es-ES', { timeZone: 'Europe/Oslo', dateStyle: 'medium', timeStyle: 'short' })
    : 'pendiente';
  const labels = { ok: 'Completo', operational_partial: 'Operativo parcial', failed: 'No operativo' };
  const health = document.querySelector('#health');
  health.className = `health status-${data.status}`;
  health.innerHTML = `<strong>${labels[data.status] || escapeHtml(data.status)}</strong><span>${data.series_ok}/${data.series_total} series · ${generated}</span>`;
}

function renderRegime(data) {
  const regime = data.regime || {};
  const card = document.querySelector('#regime');
  card.className = `card regime-card regime-${String(regime.regime || '').toLowerCase()}`;
  card.innerHTML = `
    <div class="regime-top"><p class="eyebrow">RÉGIMEN OBSERVADO</p><span>${regime.triple_active ?? 0}/3 señal triple</span></div>
    <div class="regime-code">${escapeHtml(regime.regime || '—')}</div>
    <h2>${escapeHtml(regime.label || 'Pendiente de datos')}</h2>
    <p class="method">${escapeHtml(regime.method_note || 'La clasificación se activará cuando exista historia suficiente.')}</p>`;
}

function renderDerived(data) {
  document.querySelector('#derived').innerHTML = (data.derived || []).map(metric => `
    <div class="metric">
      <strong>${valueText(metric.value, metric.unit)}</strong>
      <span>${escapeHtml(metric.title)}</span>
    </div>`).join('') || '<p class="empty">Pendiente de datos suficientes.</p>';

  const rows = data.series || [];
  const fresh = rows.filter(row => row.quality === 'ok').length;
  const observed = rows.filter(row => row.value != null).length;
  const official = new Set(rows.filter(row => row.value != null).map(row => row.source)).size;
  document.querySelector('#coverage').innerHTML = `
    <span><strong>${fresh}</strong> frescas</span>
    <span><strong>${observed}</strong> observadas</span>
    <span><strong>${official}</strong> productores activos</span>`;
}

function renderSignals(data) {
  const signals = data.regime?.signals || [];
  document.querySelector('#signals').innerHTML = signals.map(signal => `
    <article class="signal ${signalClass(signal.active)}">
      <span class="signal-state"><i class="dot"></i>${signal.active == null ? 'Sin dato' : signal.active ? 'Activa' : 'No activa'}</span>
      <strong>${escapeHtml(signal.label)}</strong>
      <div class="signal-value">${signalValue(signal)}</div>
      <small>${escapeHtml(signal.threshold)}</small>
      <p>${escapeHtml(signal.explanation)}</p>
    </article>`).join('') || '<p class="empty">Pendiente de historia suficiente.</p>';
}

function renderCapex(data) {
  const ids = ['CAPEX_MSFT', 'CAPEX_GOOG', 'CAPEX_AMZN', 'CAPEX_META', 'CAPEX_ORCL'];
  const rows = ids.map(id => (data.series || []).find(row => row.id === id)).filter(row => row?.value != null);
  const max = Math.max(...rows.map(row => row.value), 0);
  document.querySelector('#capex').innerHTML = rows.length ? rows
    .sort((a, b) => b.value - a.value)
    .map(row => `
      <div class="bar-row">
        <div class="bar-label"><strong>${escapeHtml(row.title.split(':')[0])}</strong><span>${fmt.format(row.value)} mM USD</span></div>
        <div class="bar-track"><i style="width:${max ? row.value / max * 100 : 0}%"></i></div>
        <small>FY terminado ${escapeHtml(row.observation_date || '—')}</small>
      </div>`).join('') : '<p class="empty">Se incorporará al validar Company Facts de la SEC.</p>';
}

function renderErrors(data) {
  const errors = data.errors || [];
  document.querySelector('#errors').innerHTML = errors.length ? `
    <details class="error-box">
      <summary>${errors.length} fuente${errors.length === 1 ? '' : 's'} con incidencia · se conserva el último dato válido cuando existe</summary>
      <ul>${errors.map(error => `<li><strong>${escapeHtml(error.series_id)}</strong> · ${escapeHtml(error.error)}</li>`).join('')}</ul>
    </details>` : '';
}

function qualityLabel(row) {
  const labels = { ok: 'Fresco', warning: 'Revisar', stale: 'Antiguo', missing: 'Sin dato' };
  return `${labels[row.quality] || row.quality}${row.age_days == null ? '' : ` · ${row.age_days} d`}`;
}

function renderGroups(query = '') {
  if (!state.latest) return;
  const needle = query.trim().toLocaleLowerCase('es');
  const rows = (state.latest.series || []).filter(row => !needle ||
    `${row.title} ${row.group} ${row.id} ${row.source}`.toLocaleLowerCase('es').includes(needle));
  const groups = rows.reduce((output, row) => {
    (output[row.group] ||= []).push(row);
    return output;
  }, {});
  document.querySelector('#groups').innerHTML = Object.entries(groups).map(([group, items], index) => `
    <details class="group" ${index < 3 || needle ? 'open' : ''}>
      <summary><span>${escapeHtml(group)}</span><small>${items.filter(item => item.value != null).length}/${items.length}</small></summary>
      <div class="table-wrap"><table>
        <thead><tr><th>Variable</th><th>Valor</th><th>Observación</th><th>Fuente</th><th>Estado</th></tr></thead>
        <tbody>${items.map(row => `<tr>
          <td>${escapeHtml(row.title)}<br><small>${escapeHtml(row.id)}</small></td>
          <td class="numeric">${valueText(row.value, row.unit)}</td>
          <td>${escapeHtml(row.observation_date || '—')}</td>
          <td>${safeSource(row.source_url, row.source)}</td>
          <td><span class="quality ${escapeHtml(row.quality)}">${escapeHtml(qualityLabel(row))}</span></td>
        </tr>`).join('')}</tbody>
      </table></div>
    </details>`).join('') || '<p class="empty">No hay coincidencias.</p>';
}

function filteredSeries(seriesId) {
  const source = state.history?.series?.[seriesId] || [];
  const clean = source
    .filter(point => point?.date && Number.isFinite(Number(point.value)))
    .map(point => ({ date: point.date, time: Date.parse(`${point.date}T00:00:00Z`), value: Number(point.value) }))
    .filter(point => Number.isFinite(point.time))
    .sort((a, b) => a.time - b.time);
  if (state.range === 'all' || !clean.length) return clean;
  const cutoff = clean[clean.length - 1].time - Number(state.range) * 86400000;
  return clean.filter(point => point.time >= cutoff);
}

function renderLineChart(containerId, config) {
  const width = 820;
  const height = 286;
  const margin = { top: 22, right: 18, bottom: 34, left: 52 };
  const datasets = config.series.map(item => ({ ...item, points: filteredSeries(item.id) })).filter(item => item.points.length);
  const container = document.querySelector(containerId);
  if (!datasets.length || datasets.every(item => item.points.length < 2)) {
    container.innerHTML = '<p class="chart-empty">Aún no hay historia suficiente.</p>';
    return;
  }

  datasets.forEach(dataset => {
    const base = dataset.points[0].value;
    dataset.display = dataset.points.map(point => ({
      ...point,
      plotted: config.normalized && base ? point.value / base * 100 : point.value,
    }));
  });
  const plotted = datasets.flatMap(dataset => dataset.display.map(point => point.plotted)).filter(Number.isFinite);
  const times = datasets.flatMap(dataset => dataset.display.map(point => point.time));
  let yMin = Math.min(...plotted);
  let yMax = Math.max(...plotted);
  const padding = yMax === yMin ? Math.max(Math.abs(yMax) * 0.05, 1) : (yMax - yMin) * 0.1;
  yMin -= padding;
  yMax += padding;
  const xMin = Math.min(...times);
  const xMax = Math.max(...times);
  const x = time => margin.left + (time - xMin) / Math.max(xMax - xMin, 1) * (width - margin.left - margin.right);
  const y = value => margin.top + (yMax - value) / Math.max(yMax - yMin, 1) * (height - margin.top - margin.bottom);

  const grid = Array.from({ length: 5 }, (_, index) => {
    const value = yMin + (yMax - yMin) * index / 4;
    const py = y(value);
    return `<line x1="${margin.left}" x2="${width - margin.right}" y1="${py}" y2="${py}" class="grid-line" />
      <text x="${margin.left - 9}" y="${py + 4}" text-anchor="end" class="axis-label">${fmt.format(value)}</text>`;
  }).join('');

  const lines = datasets.map(dataset => {
    const path = dataset.display.map((point, index) => `${index ? 'L' : 'M'}${x(point.time).toFixed(1)},${y(point.plotted).toFixed(1)}`).join(' ');
    const last = dataset.display[dataset.display.length - 1];
    return `<path d="${path}" fill="none" stroke="${dataset.color}" stroke-width="2.4" vector-effect="non-scaling-stroke" />
      <circle cx="${x(last.time)}" cy="${y(last.plotted)}" r="3.5" fill="${dataset.color}"><title>${escapeHtml(dataset.label)}: ${fmt.format(last.plotted)}</title></circle>`;
  }).join('');

  const startDate = dateFmt.format(new Date(xMin));
  const endDate = dateFmt.format(new Date(xMax));
  const legend = datasets.map(dataset => {
    const last = dataset.display[dataset.display.length - 1];
    return `<span><i style="background:${dataset.color}"></i>${escapeHtml(dataset.label)} <strong>${fmt.format(last.plotted)}</strong></span>`;
  }).join('');

  container.innerHTML = `<div class="chart-legend">${legend}</div>
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
      ${grid}${lines}
      <text x="${margin.left}" y="${height - 8}" class="axis-label">${startDate}</text>
      <text x="${width - margin.right}" y="${height - 8}" text-anchor="end" class="axis-label">${endDate}</text>
    </svg>`;
}

function renderCharts() {
  renderLineChart('#chart-us', { normalized: false, series: [
    { id: 'DGS2', label: '2 años', color: COLORS.blue },
    { id: 'DGS10', label: '10 años', color: COLORS.gold },
    { id: 'DGS30', label: '30 años', color: COLORS.red },
  ] });
  renderLineChart('#chart-global', { normalized: false, series: [
    { id: 'DGS10', label: 'EE. UU.', color: COLORS.gold },
    { id: 'IRLTLT01JPM156N', label: 'Japón', color: COLORS.red },
    { id: 'IRLTLT01DEM156N', label: 'Alemania', color: COLORS.blue },
    { id: 'IRLTLT01GBM156N', label: 'R. Unido', color: COLORS.violet },
    { id: 'IRLTLT01NOM156N', label: 'Noruega', color: COLORS.green },
    { id: 'IRLTLT01EZM156N', label: 'Euro AAA', color: COLORS.cyan },
  ] });
  renderLineChart('#chart-reserve', { normalized: true, series: [
    { id: 'DTWEXBGS', label: 'Dólar', color: COLORS.blue },
    { id: 'GOLDAMGBD228NLBM', label: 'Oro', color: COLORS.gold },
    { id: 'CBBTCUSD', label: 'Bitcoin', color: COLORS.orange },
  ] });
  renderLineChart('#chart-norway', { normalized: true, series: [
    { id: 'DEXNOUS', label: 'NOK/USD', color: COLORS.red },
    { id: 'IRLTLT01NOM156N', label: 'Bono 10a', color: COLORS.green },
    { id: 'DCOILBRENTEU', label: 'Brent', color: COLORS.gold },
  ] });
}

function render() {
  const data = state.latest;
  renderHealth(data);
  renderRegime(data);
  renderDerived(data);
  renderSignals(data);
  renderCapex(data);
  renderErrors(data);
  renderGroups(document.querySelector('#filter').value);
  renderCharts();
}

document.querySelector('#filter').addEventListener('input', event => renderGroups(event.target.value));
document.querySelectorAll('[data-range]').forEach(button => button.addEventListener('click', () => {
  state.range = button.dataset.range === 'all' ? 'all' : Number(button.dataset.range);
  document.querySelectorAll('[data-range]').forEach(item => item.classList.toggle('selected', item === button));
  renderCharts();
}));

async function loadJson(path) {
  const response = await fetch(path, { cache: 'no-store' });
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

Promise.all([loadJson('data/latest.json'), loadJson('data/series.json')])
  .then(([latest, history]) => {
    state.latest = latest;
    state.history = history;
    render();
  })
  .catch(error => {
    document.querySelector('#health').textContent = 'Error de carga';
    document.querySelector('#regime').className = 'card regime-card';
    document.querySelector('#regime').innerHTML = `<p class="eyebrow">ERROR</p><h2>No se pudieron leer los datos</h2><p>${escapeHtml(error.message)}</p>`;
  });
