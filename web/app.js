const fmt = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 2 });
let latest = null;

function signalClass(active) { return active === true ? 'active' : active === false ? 'inactive' : 'unknown'; }
function valueText(value, unit = '') { return value == null ? '—' : `${fmt.format(value)} ${unit}`.trim(); }

function render(data) {
  latest = data;
  const generated = data.generated_at ? new Date(data.generated_at).toLocaleString('es-ES') : 'pendiente';
  document.querySelector('#health').textContent = `${data.status} · ${data.series_ok}/${data.series_total} · ${generated}`;

  document.querySelector('#regime').innerHTML = `
    <p class="eyebrow">RÉGIMEN OBSERVADO</p>
    <div class="regime-code">${data.regime.regime}</div>
    <h2>${data.regime.label}</h2>
    <p class="method">${data.regime.method_note || 'La clasificación se activará después de la primera carga.'}</p>`;

  document.querySelector('#derived').innerHTML = (data.derived || []).map(m => `
    <div class="metric"><strong>${valueText(m.value, m.unit)}</strong><span>${m.title}</span></div>`).join('') || '<p class="subtitle">Pendiente de datos.</p>';

  document.querySelector('#signals').innerHTML = (data.regime.signals || []).map(s => `
    <article class="signal ${signalClass(s.active)}">
      <span><i class="dot"></i>${s.active == null ? 'Sin dato' : s.active ? 'Activo' : 'No activo'}</span>
      <strong>${s.label}</strong>
      <div>${valueText(s.value)}</div>
      <small>${s.threshold}</small>
    </article>`).join('') || '<p class="subtitle">Pendiente de datos.</p>';
  renderGroups('');
}

function renderGroups(query) {
  if (!latest) return;
  const needle = query.trim().toLowerCase();
  const rows = (latest.series || []).filter(s => !needle || `${s.title} ${s.group} ${s.id}`.toLowerCase().includes(needle));
  const groups = Object.groupBy ? Object.groupBy(rows, s => s.group) : rows.reduce((acc, s) => ((acc[s.group] ||= []).push(s), acc), {});
  document.querySelector('#groups').innerHTML = Object.entries(groups).map(([group, items]) => `
    <section class="group"><h3>${group}</h3><div class="table-wrap"><table>
      <thead><tr><th>Variable</th><th>Valor</th><th>Observación</th><th>Frescura</th></tr></thead>
      <tbody>${items.map(s => `<tr><td>${s.title}<br><small>${s.id}</small></td><td>${valueText(s.value, s.unit)}</td><td>${s.observation_date || '—'}</td><td><span class="quality ${s.quality}">${s.quality}${s.age_days == null ? '' : ` · ${s.age_days} d`}</span></td></tr>`).join('')}</tbody>
    </table></div></section>`).join('');
}

document.querySelector('#filter').addEventListener('input', e => renderGroups(e.target.value));
fetch('data/latest.json', { cache: 'no-store' }).then(r => {
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}).then(render).catch(error => {
  document.querySelector('#health').textContent = 'Error de carga';
  document.querySelector('#regime').innerHTML = `<h2>No se pudo leer data/latest.json</h2><p>${error.message}</p>`;
});

