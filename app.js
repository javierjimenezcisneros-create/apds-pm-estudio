/* ============================================================
   POMBO ESTUDIO — app.js
   Usa MASTER_DATA, GLOBAL_DATA, PLANNING_DATA, META
   IDs de DOM según head.html: #view, #tabs, #export-btn,
   #week-badge, #update-badge
   ============================================================ */

/* ── localStorage ─────────────────────────────────────────── */
const S = {
  key: (pid, f) => `pombo_${pid}_${f}`,
  get: (pid, f, d = '') => { try { return localStorage.getItem(S.key(pid,f)) ?? d; } catch { return d; } },
  set: (pid, f, v) => { try { localStorage.setItem(S.key(pid,f), v); } catch {} },
  toggle: (pid, f) => { const v = S.get(pid,f,'0')==='1'?'0':'1'; S.set(pid,f,v); return v==='1'; }
};

/* ── Índices ──────────────────────────────────────────────── */
let _gIdx = null, _pIdx = null;

function buildIndexes() {
  _gIdx = {}; (GLOBAL_DATA||[]).forEach(g => { _gIdx[g.id] = g; });
  _pIdx = {}; ((PLANNING_DATA||{}).proyectos||[]).forEach(p => { _pIdx[p.id] = p; });
}

const globalOf = id => _gIdx?.[id] || null;
const planOf   = id => _pIdx?.[id] || null;

function enrich(p) {
  return { ...p, _g: globalOf(p.id), _p: planOf(p.id) };
}

/* ── Semanas ──────────────────────────────────────────────── */
const hoySemana = () => META?.hoy_semana || '';
const VENTANA   = 12; // semanas visibles en vista general

function semanaWindow() {
  const sems = PLANNING_DATA?.semanas || [];
  const i = sems.indexOf(hoySemana());
  return sems.slice(Math.max(0,i), Math.max(0,i) + VENTANA);
}

/* ── Personas: exclusión y obtención ────────────────────────*/
const EXCLUIR_PERSONAS = ['Alicia'];

function getPersonas() {
  const s = new Set();
  (MASTER_DATA||[]).forEach(p => (p.equipo||[]).forEach(n => {
    if (n && typeof n === 'string' && n.trim() && !/^\d+$/.test(n.trim()) && !EXCLUIR_PERSONAS.includes(n.trim())) {
      s.add(n.trim());
    }
  }));
  return [...s].sort();
}

/* ── Nivel de atención (prioridad) ─────────────────────────*/
function atLevel(proj) {
  const a = (proj._g?.atencion || '').toUpperCase();
  if (a.includes('MÁXIMA') || a.includes('MAXIMA')) return 0;
  if (a.includes('ALTA'))                            return 1;
  if (a.includes('SEGUIMIENTO'))                     return 2;
  if (a.includes('ESTABLE'))                         return 3;
  return 3; // null/vacío = CONTROLADO
}

/* ── Helpers estilo ──────────────────────────────────────── */
function deptTag(dpto) {
  const d = (dpto||'').toLowerCase();
  if (d.includes('vivienda'))    return ['tag-viv','VIVIENDA'];
  if (d.includes('restaurante')) return ['tag-rest','REST'];
  if (d.includes('hotel'))       return ['tag-hot','HOTEL'];
  return ['tag-out', dpto||'—'];
}

function riskTag(nivel) {
  const n = (nivel||'').toUpperCase();
  if (n.includes('MÁXIMA')||n.includes('MAXIMA')) return ['tag-crit','● CRÍTICO'];
  if (n.includes('ALTA'))                          return ['tag-alto','● ALTO'];
  if (n.includes('SEGUIMIENTO'))                   return ['tag-med','● MED'];
  if (n.includes('ESTABLE'))                       return ['tag-baj','● OK'];
  return ['tag-out','—'];
}

function tagHtml(cls, txt) {
  return `<span class="tag ${cls}">${txt}</span>`;
}

/* ── Helpers texto ───────────────────────────────────────── */
function abrev(txt) {
  if (!txt) return '';
  const t = txt.toUpperCase();
  if (t.includes('PROY')) return 'PRY';
  if (t.includes('OBRA')) return 'OBR';
  if (t.includes('MONTAJ')) return 'MNT';
  if (t.includes('ENTREGA')) return 'ENT';
  if (t.includes('RENDER')) return 'RND';
  if (t.includes('VISITA')) return 'VIS';
  if (t.includes('PEDIDO')) return 'PED';
  return txt.slice(0,3).toUpperCase();
}

function faseColor(txt) {
  const t = (txt||'').toUpperCase();
  if (t.includes('PROY') || t.includes('ANTEPR')) return 'ph1';
  if (t.includes('OBRA'))    return 'ph2';
  if (t.includes('MONTAJ'))  return 'ph3';
  if (t.includes('ENTREGA')) return 'ph4';
  if (t.includes('RENDER'))  return 'ph5';
  if (t.includes('VISITA'))  return 'ph6';
  if (t.includes('PEDIDO'))  return 'ph7';
  if (t.includes('PARAD') || t.includes('ESPERA')) return 'ph9';
  return 'ph1';
}

function row2(k, v) {
  return `<tr><td style="color:var(--ink3);font-size:10px;letter-spacing:.08em;text-transform:uppercase;padding:4px 0;width:110px;">${k}</td><td style="padding:4px 0;">${v}</td></tr>`;
}

/* ── Semana number helper ────────────────────────────────── */
function weekNum(semStr) {
  // semStr format: "W41/2026" → 41
  if (!semStr) return 0;
  const m = semStr.match(/W(\d+)/i);
  return m ? parseInt(m[1], 10) : 0;
}

function yearNum(semStr) {
  if (!semStr) return 0;
  const m = semStr.match(/\/(\d{4})/);
  return m ? parseInt(m[1], 10) : 0;
}

function semToSortKey(semStr) {
  return yearNum(semStr) * 100 + weekNum(semStr);
}

/* ── hoySemana helpers ────────────────────────────────────── */
function isThisWeek(semStr) {
  return semStr === hoySemana();
}

function isNextNWeeks(semStr, n) {
  const allSems = PLANNING_DATA?.semanas || [];
  const hoyIdx = allSems.indexOf(hoySemana());
  if (hoyIdx < 0) return false;
  const idx = allSems.indexOf(semStr);
  return idx > hoyIdx && idx <= hoyIdx + n;
}

function projHasActivityThisWeek(proj) {
  const hoy = hoySemana();
  return (proj._p?.timeline || []).some(t => t.semana === hoy);
}

function projHasActivityInWindow(proj, startOffset, endOffset) {
  const allSems = PLANNING_DATA?.semanas || [];
  const hoyIdx  = allSems.indexOf(hoySemana());
  if (hoyIdx < 0) return false;
  const window = allSems.slice(hoyIdx + startOffset, hoyIdx + endOffset + 1);
  return (proj._p?.timeline || []).some(t => window.includes(t.semana));
}

/* ── Gantt general (ventana 12 sem) ─────────────────────── */
function ganttGeneral(proj) {
  const ventana = semanaWindow();
  const plan    = proj._p;
  const hoy     = hoySemana();
  if (!ventana.length) return '';

  let cellsHtml = '<div class="gantt-grid">';
  ventana.forEach(sem => {
    const esHoy  = sem === hoy;
    const entry  = (plan?.timeline || []).find(t => t.semana === sem);
    const act    = entry?.actividades?.[0];
    const texto  = act?.texto || '';
    let phCls    = texto ? faseColor(texto) : '';
    let cls      = `gantt-cell${phCls ? ' '+phCls+' filled' : ''}${esHoy ? ' gantt-cell-hoy' : ''}`;
    const title  = `${sem}${texto ? ': '+texto : ''}`;
    cellsHtml += `<div class="${cls}" title="${title}" data-sem="${sem}" data-id="${proj.id}">
      ${texto ? `<span class="gantt-label">${abrev(texto)}</span>` : ''}
    </div>`;
  });
  cellsHtml += '</div>';

  let weeksHtml = '<div class="gantt-weeks">';
  ventana.forEach(sem => {
    weeksHtml += `<div class="gantt-week${sem===hoy?' gantt-week-hoy':''}">${sem.split('/')[0]}</div>`;
  });
  weeksHtml += '</div>';

  return `<div class="gantt" style="overflow-x:auto;">${weeksHtml}${cellsHtml}</div>`;
}

/* ── Gantt completo (modal) ─────────────────────────────── */
function ganttCompleto(proj) {
  const sems = PLANNING_DATA?.semanas || [];
  const plan  = proj._p;
  const hoy   = hoySemana();
  if (!sems.length) return '<p style="color:var(--ink3);font-size:12px;">Sin datos de planning.</p>';

  const N = sems.length;

  let weeksHtml = `<div class="gantt-weeks" style="display:grid;grid-template-columns:repeat(${N},minmax(28px,1fr));">`;
  sems.forEach(sem => {
    weeksHtml += `<div class="gantt-week${sem===hoy?' gantt-week-hoy':''}">${sem.split('/')[0]}</div>`;
  });
  weeksHtml += '</div>';

  let cellsHtml = `<div class="gantt-grid" style="display:grid;grid-template-columns:repeat(${N},minmax(28px,1fr));">`;
  sems.forEach(sem => {
    const esHoy  = sem === hoy;
    const entry  = (plan?.timeline || []).find(t => t.semana === sem);
    const texto  = entry?.actividades?.[0]?.texto || '';
    let phCls    = texto ? faseColor(texto) : '';
    let cls      = `gantt-cell${phCls ? ' '+phCls+' filled' : ''}${esHoy ? ' gantt-cell-hoy' : ''}`;
    cellsHtml   += `<div class="${cls}" title="${sem}${texto?': '+texto:''}">${texto ? `<span class="gantt-label">${abrev(texto)}</span>` : ''}</div>`;
  });
  cellsHtml += '</div>';

  return `<div class="gantt" style="overflow-x:auto;">${weeksHtml}${cellsHtml}</div>`;
}

/* ── Tarjeta de proyecto ─────────────────────────────────── */
function projCard(proj, opts={}) {
  const g    = proj._g;
  const done = S.get(proj.id,'done') === '1';
  const [dCls, dTxt] = deptTag(proj.dpto);
  const [rCls, rTxt] = riskTag(g?.atencion);
  const hito    = g?.proximo_hito || '';
  const fecha   = g?.fecha_hito   || '';
  const bloq    = g?.bloqueador   || '';
  const equipo  = (proj.equipo||[]).map(e => `<span style="font-size:11px;color:var(--ink3)">${e}</span>`).join(' · ');
  const note    = S.get(proj.id,'note');

  const hitoHtml = hito
    ? `<div class="hito-row"><span class="hito-text">${hito}</span>${fecha ? `<span class="hito-date">${fecha}</span>` : ''}</div>`
    : '';
  const bloqHtml = bloq
    ? `<div style="font-size:11.5px;color:var(--crit);margin:4px 0;">⚠ ${bloq}</div>`
    : '';
  const ganttHtml   = opts.gantt !== false ? ganttGeneral(proj) : '';
  const equipoHtml  = equipo ? `<div style="margin-top:6px;">${equipo}</div>` : '';

  return `<div class="proj-card${done ? ' proj-done' : ''}" data-id="${proj.id}">
    <div class="proj-top">
      <div>
        <div class="proj-tags" style="margin-bottom:5px;">
          ${tagHtml(dCls,dTxt)} ${tagHtml(rCls,rTxt)}
          ${proj.fase ? `<span class="tag tag-out">${proj.fase}</span>` : ''}
        </div>
        <div class="proj-name" style="cursor:pointer;" data-open="${proj.id}">${proj.nombre}</div>
      </div>
      <div style="display:flex;gap:6px;align-items:flex-start;flex-shrink:0;">
        <button class="btn-done btn-ghost" data-done="${proj.id}" style="font-size:16px;padding:2px 8px;line-height:1;">${done ? '✓' : '○'}</button>
        <button class="btn-ghost btn-open" data-open="${proj.id}" style="font-size:11px;">↗</button>
      </div>
    </div>
    ${hitoHtml}${bloqHtml}${equipoHtml}
    ${ganttHtml}
    <div class="note-area" style="margin-top:10px;">
      <label>Nota</label>
      <textarea data-note="${proj.id}" rows="1" placeholder="Nota privada…">${note}</textarea>
    </div>
  </div>`;
}

/* ── Modal de proyecto ───────────────────────────────────── */
let _modalId = null;

function openModal(id) {
  const raw = (MASTER_DATA||[]).find(p => p.id === id);
  if (!raw) return;
  _modalId = id;
  const proj = enrich(raw);
  const g    = proj._g;

  const equipoHtml = (proj.equipo||[]).map(e =>
    `<span class="tag tag-out">${e}</span>`
  ).join(' ');

  // DECO section — only if any deco field is not null/empty
  const hasDeco = proj.deco_cerrada || proj.presupuesto_deco_aceptado || proj.pedidos_confirmados;
  const decoHtml = hasDeco
    ? `<div style="margin-bottom:12px;">
        <div class="eyebrow" style="margin-bottom:6px;">Deco</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          <span class="tag ${proj.deco_cerrada==='SÍ'?'tag-baj':'tag-out'}">Deco cerrada: ${proj.deco_cerrada||'—'}</span>
          <span class="tag ${proj.presupuesto_deco_aceptado==='SÍ'?'tag-baj':'tag-out'}">Ppto aceptado: ${proj.presupuesto_deco_aceptado||'—'}</span>
          <span class="tag ${proj.pedidos_confirmados==='SÍ'?'tag-baj':'tag-out'}">Pedidos: ${proj.pedidos_confirmados||'—'}</span>
        </div>
      </div>`
    : '';

  const html = `
    <div class="modal-bg" id="modal-bg">
      <div class="modal">
        <div class="modal-head">
          <div>
            <div class="modal-title">${proj.nombre}</div>
            <div class="modal-sub">${proj.dpto||''} · ${proj.fase||''}</div>
          </div>
          <button class="modal-close" id="modal-close">×</button>
        </div>
        <div class="modal-body" style="max-height:70vh;overflow-y:auto;">

          <!-- IDENTIDAD -->
          <div style="margin-bottom:12px;">
            <div class="eyebrow" style="margin-bottom:6px;">Identidad</div>
            <div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:6px;">
              ${tagHtml(...deptTag(proj.dpto))}
              ${tagHtml(...riskTag(g?.atencion))}
            </div>
            ${equipoHtml ? `<div style="margin-bottom:6px;">${equipoHtml}</div>` : ''}
            <table style="width:100%;font-size:12.5px;border-collapse:collapse;">
              ${row2('Estado', proj.estado||'—')}
              ${row2('Fase', proj.fase||'—')}
            </table>
          </div>

          <!-- GLOBAL -->
          <div style="margin-bottom:12px;">
            <div class="eyebrow" style="margin-bottom:6px;">Global</div>
            ${g?.bloqueador ? `<div style="color:var(--crit);font-size:12.5px;margin-bottom:8px;">⚠ ${g.bloqueador}</div>` : ''}
            <table style="width:100%;font-size:12.5px;border-collapse:collapse;">
              ${row2('Próximo hito', g?.proximo_hito||'—')}
              ${row2('Fecha hito', g?.fecha_hito||'—')}
              ${g?.obs ? row2('Obs', g.obs) : ''}
            </table>
          </div>

          <!-- DECO -->
          ${decoHtml}

          <!-- FECHAS -->
          <div style="margin-bottom:12px;">
            <div class="eyebrow" style="margin-bottom:6px;">Fechas</div>
            <table style="width:100%;font-size:12.5px;border-collapse:collapse;">
              ${row2('Fin obra', proj.fin_obra||'—')}
              ${row2('Montaje', proj.montaje||'—')}
              ${row2('Fin oficial', proj.fin_oficial||'—')}
            </table>
          </div>

          <!-- PLANNING -->
          <div id="modal-planning-section" style="margin-bottom:12px;">
            <div class="eyebrow" style="margin-bottom:8px;">Planning</div>
            <button class="btn-primary" id="btn-planning-completo">VER PLANNING COMPLETO →</button>
            <div id="modal-gantt-preview" style="margin-top:10px;">${ganttGeneral(proj)}</div>
          </div>

          <!-- NOTA PERSONAL -->
          <div class="note-area" style="margin-top:14px;">
            <label>Nota personal</label>
            <textarea id="modal-note" rows="3" placeholder="Solo en este dispositivo…">${S.get(proj.id,'note')}</textarea>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn-ghost" id="modal-close2">Cerrar</button>
        </div>
      </div>
    </div>`;

  document.getElementById('modal-bg')?.remove();
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('modal-close')?.addEventListener('click', closeModal);
  document.getElementById('modal-close2')?.addEventListener('click', closeModal);
  document.getElementById('modal-bg')?.addEventListener('click', e => {
    if (e.target.id === 'modal-bg') closeModal();
  });
  document.getElementById('modal-note')?.addEventListener('change', e => {
    S.set(_modalId, 'note', e.target.value);
  });

  // VER PLANNING COMPLETO
  document.getElementById('btn-planning-completo')?.addEventListener('click', () => {
    const section = document.getElementById('modal-planning-section');
    if (!section) return;
    section.innerHTML = `
      <div class="eyebrow" style="margin-bottom:8px;">Planning completo</div>
      <div style="overflow-x:auto;">${ganttCompleto(proj)}</div>`;
  });
}

function closeModal() {
  const note = document.getElementById('modal-note');
  if (note && _modalId) S.set(_modalId, 'note', note.value);
  document.getElementById('modal-bg')?.remove();
  _modalId = null;
}

/* ── Agrupación de personas por departamento ─────────────── */
function getPersonasByGroup() {
  const personas = getPersonas();
  const DEPTS    = ['HOTELES', 'RESTAURANTES', 'VIVIENDA', 'SIN ASIGNAR'];

  function primaryDept(nombre) {
    const counts = { HOTELES: 0, RESTAURANTES: 0, VIVIENDA: 0 };
    (MASTER_DATA||[]).forEach(p => {
      if (!(p.equipo||[]).includes(nombre)) return;
      const d = (p.dpto||'').toUpperCase();
      if (d.includes('HOTEL'))       counts.HOTELES++;
      else if (d.includes('RESTAURANTE')) counts.RESTAURANTES++;
      else if (d.includes('VIVIENDA'))    counts.VIVIENDA++;
    });
    // Most frequent dept; ties: HOTELES > RESTAURANTES > VIVIENDA > SIN ASIGNAR
    let best = 'SIN ASIGNAR', bestCount = 0;
    for (const dept of ['HOTELES', 'RESTAURANTES', 'VIVIENDA']) {
      if (counts[dept] > bestCount) { bestCount = counts[dept]; best = dept; }
    }
    return best;
  }

  const groups = {};
  DEPTS.forEach(d => { groups[d] = []; });
  personas.forEach(n => {
    const dept = primaryDept(n);
    groups[dept].push(n);
  });
  // Sort alphabetically within each group
  DEPTS.forEach(d => groups[d].sort());
  return { groups, order: DEPTS };
}

/* ── Tabs ─────────────────────────────────────────────────── */
let curTab = 'javi';

function buildTabs() {
  const tabsEl = document.getElementById('tabs');
  if (!tabsEl) return;

  const { groups, order } = getPersonasByGroup();

  let html = '';

  // Fixed tabs
  html += `<button class="tab tab-master ${curTab==='javi'?'active':''}" data-tab="javi">JAVI — CENTRO DE CONTROL</button>`;
  html += `<button class="tab ${curTab==='alejandra'?'active':''}" data-tab="alejandra">ALEJANDRA — DIRECCIÓN</button>`;

  // Team tabs grouped by department
  order.forEach(dept => {
    const people = groups[dept];
    if (!people.length) return;

    html += `<span class="tab-group-label">${dept}</span>`;
    people.forEach(nombre => {
      const slug = nombre.toLowerCase().replace(/\s+/g,'_');
      const id   = `p__${slug}`;
      html += `<button class="tab ${curTab===id?'active':''}" data-tab="${id}">${nombre}</button>`;
    });
  });

  tabsEl.innerHTML = html;
}

function activateTab(id) {
  curTab = id;
  document.querySelectorAll('#tabs .tab').forEach(b => b.classList.toggle('active', b.dataset.tab === id));

  if (id === 'javi')           renderJavi();
  else if (id === 'alejandra') renderAlejandra();
  else if (id.startsWith('p__')) {
    const slug   = id.slice(3);
    const nombre = getPersonas().find(n => n.toLowerCase().replace(/\s+/g,'_') === slug);
    if (nombre) renderPersona(nombre);
  }
}

/* ── Render Javi — CENTRO DE CONTROL ──────────────────────*/
function renderJavi() {
  const todos  = (MASTER_DATA||[]).map(enrich);
  const sem    = hoySemana();
  const wNum   = sem.split('/')[0] || sem;

  // Calcular número de semana display
  const semLabel = wNum ? `Semana ${wNum}` : 'Esta semana';

  const groups = [
    { level: 0, label: '● ALERTA',       labelCls: 'tag-crit', projs: [] },
    { level: 1, label: '● ATENCIÓN',     labelCls: 'tag-alto', projs: [] },
    { level: 2, label: '● SEGUIMIENTO',  labelCls: '',          projs: [] },
    { level: 3, label: '● CONTROLADO',   labelCls: '',          projs: [] },
  ];

  todos.forEach(p => {
    const lvl = atLevel(p);
    groups[lvl].projs.push(p);
  });

  let html = `<div class="view-head">
    <div>
      <div class="view-title">CENTRO DE CONTROL</div>
      <div class="view-sub">${semLabel} · ${todos.length} proyectos</div>
    </div>
  </div>`;

  groups.forEach(g => {
    if (!g.projs.length) return;
    const showGantt = g.level <= 1; // ALERTA and ATENCIÓN get gantt

    const labelHtml = g.labelCls
      ? `<span class="eyebrow">${tagHtml(g.labelCls, g.label)}</span>`
      : `<span class="eyebrow">${g.label}</span>`;

    html += `<div class="panel">
      <div class="panel-head">${labelHtml}</div>
      ${g.projs.map(p => projCard(p, { gantt: showGantt })).join('')}
    </div>`;
  });

  document.getElementById('view').innerHTML = html;
}

/* ── Render Alejandra — DIRECCIÓN ────────────────────────── */
function renderAlejandra() {
  const todos = (MASTER_DATA||[]).map(enrich);
  const sem   = hoySemana();
  const wNum  = sem.split('/')[0] || sem;

  const alerta   = todos.filter(p => atLevel(p) === 0);
  const atencion = todos.filter(p => atLevel(p) === 1);

  // ESTA SEMANA: projects with activity in hoySemana() in PLANNING_DATA
  const estaSemana = todos.filter(p => projHasActivityThisWeek(p));

  // PRÓXIMOS HITOS: top 12 sorted by fecha_hito nearest first
  const conHito = todos.filter(p => p._g?.fecha_hito)
    .sort((a,b) => {
      const da = a._g.fecha_hito, db = b._g.fecha_hito;
      return da < db ? -1 : da > db ? 1 : 0;
    })
    .slice(0, 12);

  let html = `<div class="view-head">
    <div>
      <div class="view-title">DIRECCIÓN</div>
      <div class="view-sub">Semana ${wNum}</div>
    </div>
  </div>`;

  // ALERTA
  html += `<div class="panel">
    <div class="panel-head"><span class="eyebrow">${tagHtml('tag-crit','● ALERTA')}</span></div>
    ${alerta.length
      ? alerta.map(p => projCard(p, {gantt:false})).join('')
      : '<p class="panel-note">Sin proyectos en alerta.</p>'}
  </div>`;

  // ATENCIÓN
  html += `<div class="panel">
    <div class="panel-head"><span class="eyebrow">${tagHtml('tag-alto','● ATENCIÓN')}</span></div>
    ${atencion.length
      ? atencion.map(p => projCard(p, {gantt:false})).join('')
      : '<p class="panel-note">Sin alertas de atención.</p>'}
  </div>`;

  // ESTA SEMANA table
  if (estaSemana.length) {
    html += `<div class="panel">
      <div class="panel-head"><span class="eyebrow">ESTA SEMANA</span></div>
      <div class="tbl-wrap"><table class="tbl">
        <thead><tr>
          <th>Proyecto</th><th>Dpto</th><th>Actividad</th><th>Próximo hito</th><th>Fecha</th>
        </tr></thead>
        <tbody>
          ${estaSemana.map(p => {
            const timeline = p._p?.timeline || [];
            const entry    = timeline.find(t => t.semana === sem);
            const act      = (entry?.actividades||[]).map(a=>a.texto).join(', ') || '—';
            return `<tr style="cursor:pointer;" data-open="${p.id}">
              <td><strong>${p.nombre}</strong></td>
              <td>${tagHtml(...deptTag(p.dpto))}</td>
              <td>${act}</td>
              <td>${p._g?.proximo_hito||'—'}</td>
              <td style="color:var(--cop);">${p._g?.fecha_hito||'—'}</td>
            </tr>`;
          }).join('')}
        </tbody>
      </table></div>
    </div>`;
  }

  // PRÓXIMOS HITOS table
  if (conHito.length) {
    html += `<div class="panel">
      <div class="panel-head"><span class="eyebrow">PRÓXIMOS HITOS</span></div>
      <div class="tbl-wrap"><table class="tbl">
        <thead><tr>
          <th>Proyecto</th><th>Dpto</th><th>Hito</th><th>Fecha</th>
        </tr></thead>
        <tbody>
          ${conHito.map(p => `<tr style="cursor:pointer;" data-open="${p.id}">
            <td><strong>${p.nombre}</strong></td>
            <td>${tagHtml(...deptTag(p.dpto))}</td>
            <td>${p._g?.proximo_hito||'—'}</td>
            <td style="color:var(--cop);">${p._g?.fecha_hito||'—'}</td>
          </tr>`).join('')}
        </tbody>
      </table></div>
    </div>`;
  }

  document.getElementById('view').innerHTML = html;
}

/* ── Render Persona ──────────────────────────────────────── */
function renderPersona(nombre) {
  const todos = (MASTER_DATA||[]).filter(p => (p.equipo||[]).includes(nombre)).map(enrich);
  const sem   = hoySemana();

  // 1. PRIORIDAD: atLevel <= 1 (ALERTA or ATENCIÓN)
  const prioridad = todos.filter(p => atLevel(p) <= 1).sort((a,b) => atLevel(a) - atLevel(b));
  const prioIds   = new Set(prioridad.map(p => p.id));

  // 2. ESTA SEMANA: activity this week, not already in PRIORIDAD
  const estaSemana = todos.filter(p => !prioIds.has(p.id) && projHasActivityThisWeek(p));
  const estaIds    = new Set(estaSemana.map(p => p.id));

  // 3. PRÓXIMAS SEMANAS: activity in next 4 weeks (not this week), not in PRIORIDAD
  const proximasSemanas = todos.filter(p => {
    if (prioIds.has(p.id) || estaIds.has(p.id)) return false;
    return projHasActivityInWindow(p, 1, 4);
  });
  const proxIds = new Set(proximasSemanas.map(p => p.id));

  // 4. MIS PROYECTOS: rest
  const misProyectos = todos.filter(p => !prioIds.has(p.id) && !estaIds.has(p.id) && !proxIds.has(p.id));

  let html = `<div class="view-head">
    <div>
      <div class="view-title">${nombre}</div>
      <div class="view-sub">${todos.length} proyecto${todos.length!==1?'s':''}</div>
    </div>
  </div>`;

  if (prioridad.length) {
    html += `<div class="panel">
      <div class="panel-head"><span class="eyebrow">PRIORIDAD</span></div>
      ${prioridad.map(p => projCard(p, {gantt:false})).join('')}
    </div>`;
  }

  if (estaSemana.length) {
    html += `<div class="panel">
      <div class="panel-head"><span class="eyebrow">ESTA SEMANA</span></div>
      ${estaSemana.map(p => projCard(p, {gantt:true})).join('')}
    </div>`;
  }

  if (proximasSemanas.length) {
    html += `<div class="panel">
      <div class="panel-head"><span class="eyebrow">PRÓXIMAS SEMANAS</span></div>
      ${proximasSemanas.map(p => projCard(p, {gantt:false})).join('')}
    </div>`;
  }

  if (misProyectos.length) {
    html += `<div class="panel">
      <div class="panel-head"><span class="eyebrow">MIS PROYECTOS</span></div>
      ${misProyectos.map(p => projCard(p, {gantt:false})).join('')}
    </div>`;
  }

  if (!todos.length) {
    html += '<p class="panel-note" style="margin-top:20px;">Sin proyectos asignados.</p>';
  }

  document.getElementById('view').innerHTML = html;
}

/* ── Exportar ─────────────────────────────────────────────── */
function exportar() {
  const hoy = new Date().toLocaleDateString('es-ES');
  const sem = hoySemana();
  const lines = [`POMBO ESTUDIO — ${hoy} (${sem})`, '='.repeat(50), ''];

  ['vivienda','restaurantes','hoteles'].forEach(dpto => {
    const ps = (MASTER_DATA||[]).filter(p => (p.dpto||'').toLowerCase().includes(dpto));
    if (!ps.length) return;
    lines.push(`\n── ${dpto.toUpperCase()} (${ps.length}) ──`);
    ps.forEach(p => {
      const g = globalOf(p.id);
      lines.push(`  ${p.nombre}`);
      if (g?.atencion)     lines.push(`    ${g.atencion}`);
      if (g?.proximo_hito) lines.push(`    → ${g.proximo_hito}${g.fecha_hito?' ('+g.fecha_hito+')':''}`);
      if (g?.bloqueador)   lines.push(`    ⚠ ${g.bloqueador}`);
    });
  });

  const blob = new Blob([lines.join('\n')], {type:'text/plain;charset=utf-8'});
  const a    = document.createElement('a');
  a.href     = URL.createObjectURL(blob);
  a.download = `pombo_${sem.replace('/','_')}.txt`;
  a.click();
}

/* ── Eventos ──────────────────────────────────────────────── */
function wireEvents() {
  // Tabs
  document.getElementById('tabs')?.addEventListener('click', e => {
    const b = e.target.closest('.tab');
    if (b) activateTab(b.dataset.tab);
  });

  // Clic en vista (delegado)
  document.getElementById('view')?.addEventListener('click', e => {
    // Abrir modal
    const open = e.target.closest('[data-open]');
    if (open) { openModal(open.dataset.open); return; }

    // Toggle done
    const done = e.target.closest('[data-done]');
    if (done) {
      const id   = done.dataset.done;
      const isDone = S.toggle(id, 'done');
      done.textContent = isDone ? '✓' : '○';
      done.closest('.proj-card')?.classList.toggle('proj-done', isDone);
      return;
    }
  });

  // Guardar nota
  document.getElementById('view')?.addEventListener('change', e => {
    const ta = e.target.closest('[data-note]');
    if (ta) S.set(ta.dataset.note, 'note', ta.value);
  });

  // Exportar
  document.getElementById('export-btn')?.addEventListener('click', exportar);

  // ESC cierra modal
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
}

/* ── Init ─────────────────────────────────────────────────── */
function init() {
  buildIndexes();
  buildTabs();
  wireEvents();
  activateTab('javi');

  // Badges del topbar
  const wb = document.getElementById('week-badge');
  if (wb) wb.textContent = hoySemana();

  const ub = document.getElementById('update-badge');
  if (ub && META?.updated) ub.textContent = 'Actualizado ' + META.updated.replace('T',' ').slice(0,16);
}

document.addEventListener('DOMContentLoaded', init);
