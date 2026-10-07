/* ============================================================
   POMBO ESTUDIO — app.js
   Usa MASTER_DATA, GLOBAL_DATA, PLANNING_DATA, META
   IDs de DOM: #view, #tabs, #export-btn, #week-badge, #update-badge
   ============================================================ */

/* ── localStorage ─────────────────────────────────────────── */
const S = {
  key:    (pid, f)    => `pombo_${pid}_${f}`,
  get:    (pid, f, d='') => { try { return localStorage.getItem(S.key(pid,f)) ?? d; } catch { return d; } },
  set:    (pid, f, v) => { try { localStorage.setItem(S.key(pid,f), v); } catch {} },
  toggle: (pid, f)    => { const v = S.get(pid,f,'0')==='1'?'0':'1'; S.set(pid,f,v); return v==='1'; }
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
const VENTANA   = 13; // semana anterior + actual + 11 siguientes

function semanaWindow() {
  const sems = PLANNING_DATA?.semanas || [];
  const i    = sems.indexOf(hoySemana());
  const from = Math.max(0, i - 1);
  return sems.slice(from, from + VENTANA);
}

/* ── Personas ─────────────────────────────────────────────── */
// Javier y Alejandra tienen pestañas fijas. Alicia excluida siempre.
const EXCLUIR_PERSONAS = ['Alicia', 'Javier', 'Alejandra'];

function getPersonas() {
  const s = new Set();
  (MASTER_DATA||[]).forEach(p => (p.equipo||[]).forEach(n => {
    if (n && typeof n === 'string' && n.trim() && !/^\d+$/.test(n.trim())
        && !EXCLUIR_PERSONAS.includes(n.trim())) {
      s.add(n.trim());
    }
  }));
  return [...s].sort();
}

/* ── Nivel de atención ────────────────────────────────────── */
// 0=ALERTA  1=ATENCIÓN  2=INFO FALTANTE  3=CONTROLADO
function atLevel(proj) {
  const a = (proj._g?.atencion || '').toUpperCase();
  if (a.includes('MÁXIMA') || a.includes('MAXIMA')) return 0;
  if (a.includes('ALTA'))                            return 1;
  if (a.includes('SEGUIMIENTO'))                     return 2;
  return 3;
}

/* ── Helpers estilo ──────────────────────────────────────── */
function deptTag(dpto) {
  const d = (dpto||'').toUpperCase();
  if (d.includes('VIVIENDA'))    return ['tag-viv',  'VIVIENDA'];
  if (d.includes('RESTAURANTE')) return ['tag-rest', 'REST'];
  if (d.includes('HOTEL'))       return ['tag-hot',  'HOTEL'];
  return ['tag-out', dpto||'—'];
}

function riskTag(nivel) {
  const n = (nivel||'').toUpperCase();
  if (n.includes('MÁXIMA')||n.includes('MAXIMA')) return ['tag-crit','● ALERTA'];
  if (n.includes('ALTA'))                          return ['tag-alto','● ATENCIÓN'];
  if (n.includes('SEGUIMIENTO'))                   return ['tag-med', '● INFO'];
  if (n.includes('ESTABLE'))                       return ['tag-baj', '● OK'];
  return ['tag-out','—'];
}

function tagHtml(cls, txt) {
  return `<span class="tag ${cls}">${txt}</span>`;
}

/* ── Helpers texto ───────────────────────────────────────── */
function abrev(txt) {
  if (!txt) return '';
  const t = txt.toUpperCase();
  if (t.includes('PROY') || t.includes('ANTEPR')) return 'PRY';
  if (t.includes('OBRA'))    return 'OBR';
  if (t.includes('MONTAJ'))  return 'MNT';
  if (t.includes('ENTREGA')) return 'ENT';
  if (t.includes('RENDER'))  return 'RND';
  if (t.includes('VISITA'))  return 'VIS';
  if (t.includes('PEDIDO'))  return 'PED';
  if (t.includes('PARAD') || t.includes('ESPERA')) return '···';
  return txt.slice(0,3).toUpperCase();
}

// Colores coherentes con la codificación del Planning Excel:
// ph1=proyecto/diseño  ph2=obra  ph3=montaje  ph4=entrega
// ph5=renders  ph6=visita  ph7=pedidos  ph9=parada/espera
function faseColor(txt) {
  const t = (txt||'').toUpperCase();
  if (t.includes('PROY') || t.includes('ANTEPR') || t.includes('DISEÑO')) return 'ph1';
  if (t.includes('OBRA'))    return 'ph2';
  if (t.includes('MONTAJ'))  return 'ph3';
  if (t.includes('ENTREGA')) return 'ph4';
  if (t.includes('RENDER'))  return 'ph5';
  if (t.includes('VISITA'))  return 'ph6';
  if (t.includes('PEDIDO'))  return 'ph7';
  if (t.includes('PARAD') || t.includes('ESPERA') || t.includes('STANDBY')) return 'ph9';
  return 'ph1';
}

function row2(k, v) {
  return `<tr>
    <td style="color:var(--ink3);font-size:10px;letter-spacing:.08em;text-transform:uppercase;
               padding:4px 0;width:115px;vertical-align:top;">${k}</td>
    <td style="padding:4px 0;font-size:12.5px;">${v}</td>
  </tr>`;
}

/* ── Activity helpers ────────────────────────────────────── */
function projHasActivityThisWeek(proj) {
  const hoy = hoySemana();
  return (proj._p?.timeline||[]).some(t => t.semana === hoy);
}

function projHasActivityInWindow(proj, startOffset, endOffset) {
  const allSems = PLANNING_DATA?.semanas || [];
  const hoyIdx  = allSems.indexOf(hoySemana());
  if (hoyIdx < 0) return false;
  const win = allSems.slice(hoyIdx + startOffset, hoyIdx + endOffset + 1);
  return (proj._p?.timeline||[]).some(t => win.includes(t.semana));
}

/* ── Gantt general (ventana operativa) ───────────────────── */
function ganttGeneral(proj) {
  const ventana = semanaWindow();
  const hoy     = hoySemana();
  if (!ventana.length) return '';

  let weeksHtml = '<div class="gantt-weeks">';
  ventana.forEach(sem => {
    weeksHtml += `<div class="gantt-week${sem===hoy?' gantt-week-hoy':''}">${sem.split('/')[0]}</div>`;
  });
  weeksHtml += '</div>';

  let cellsHtml = '<div class="gantt-grid">';
  ventana.forEach(sem => {
    const entry = (proj._p?.timeline||[]).find(t => t.semana === sem);
    const texto = entry?.actividades?.[0]?.texto || '';
    const ph    = texto ? faseColor(texto) : '';
    const cls   = `gantt-cell${ph?' '+ph+' filled':''}${sem===hoy?' gantt-cell-hoy':''}`;
    cellsHtml  += `<div class="${cls}" title="${sem}${texto?': '+texto:''}">${texto?`<span class="gantt-label">${abrev(texto)}</span>`:''}</div>`;
  });
  cellsHtml += '</div>';

  return `<div class="gantt" style="overflow-x:auto;">${weeksHtml}${cellsHtml}</div>`;
}

/* ── Gantt completo (modal ampliado) ─────────────────────── */
function ganttCompleto(proj) {
  const sems = PLANNING_DATA?.semanas || [];
  const hoy  = hoySemana();
  if (!sems.length) return '<p style="color:var(--ink3);font-size:12px;">Sin datos de planning.</p>';

  const N = sems.length;
  const colW = 'minmax(30px,1fr)';

  let weeksHtml = `<div style="display:grid;grid-template-columns:repeat(${N},${colW});gap:1px;margin-bottom:2px;">`;
  sems.forEach(sem => {
    weeksHtml += `<div style="font-size:9px;font-weight:600;letter-spacing:.04em;text-align:center;
                              padding:2px 0;color:${sem===hoy?'var(--burg)':'var(--ink3)'};">${sem.split('/')[0]}</div>`;
  });
  weeksHtml += '</div>';

  let cellsHtml = `<div style="display:grid;grid-template-columns:repeat(${N},${colW});gap:1px;">`;
  sems.forEach(sem => {
    const entry = (proj._p?.timeline||[]).find(t => t.semana === sem);
    const texto = entry?.actividades?.[0]?.texto || '';
    const ph    = texto ? faseColor(texto) : '';
    const cls   = `gantt-cell${ph?' '+ph+' filled':''}${sem===hoy?' gantt-cell-hoy':''}`;
    cellsHtml  += `<div class="${cls}" title="${sem}${texto?': '+texto:''}" style="height:28px;display:flex;align-items:center;justify-content:center;">
      ${texto?`<span class="gantt-label" style="font-size:9px;">${abrev(texto)}</span>`:''}
    </div>`;
  });
  cellsHtml += '</div>';

  return `<div style="overflow-x:auto;padding-bottom:4px;">${weeksHtml}${cellsHtml}</div>`;
}

/* ── Tarjeta de proyecto ─────────────────────────────────── */
function projCard(proj, opts={}) {
  const g    = proj._g;
  const [dCls, dTxt] = deptTag(proj.dpto);
  const [rCls, rTxt] = riskTag(g?.atencion);
  const hito  = g?.proximo_hito || '';
  const fecha = g?.fecha_hito   || '';
  const bloq  = g?.bloqueador   || '';
  const equipo = (proj.equipo||[]).join(' · ');

  const hitoHtml = hito
    ? `<div class="hito-row"><span class="hito-text">${hito}</span>${fecha?`<span class="hito-date">${fecha}</span>`:''}</div>`
    : '';
  const bloqHtml = bloq
    ? `<div style="font-size:11.5px;color:var(--crit);margin:4px 0 2px;">⚠ ${bloq}</div>`
    : '';
  const equipoHtml = equipo
    ? `<div style="font-size:11px;color:var(--ink3);margin-top:5px;">${equipo}</div>`
    : '';
  const ganttHtml = opts.gantt !== false ? ganttGeneral(proj) : '';

  return `<div class="proj-card" data-id="${proj.id}">
    <div class="proj-top">
      <div style="flex:1;min-width:0;">
        <div class="proj-tags" style="margin-bottom:5px;">
          ${tagHtml(dCls,dTxt)} ${tagHtml(rCls,rTxt)}
          ${proj.fase?`<span class="tag tag-out" style="font-size:10px;">${proj.fase}</span>`:''}
        </div>
        <div class="proj-name" style="cursor:pointer;" data-open="${proj.id}">${proj.nombre}</div>
      </div>
      <button class="btn-ghost" data-open="${proj.id}"
              style="font-size:11px;padding:4px 10px;white-space:nowrap;flex-shrink:0;">
        VER →
      </button>
    </div>
    ${hitoHtml}${bloqHtml}${equipoHtml}
    ${ganttHtml}
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

  const equipoHtml = (proj.equipo||[])
    .map(e => `<span class="tag tag-out">${e}</span>`).join(' ');

  const hasDeco = proj.deco_cerrada || proj.presupuesto_deco_aceptado || proj.pedidos_confirmados;
  const decoHtml = hasDeco ? `
    <div class="modal-section">
      <div class="modal-section-label">Deco</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <span class="tag ${proj.deco_cerrada==='SÍ'?'tag-baj':'tag-out'}">Deco cerrada: ${proj.deco_cerrada||'—'}</span>
        <span class="tag ${proj.presupuesto_deco_aceptado==='SÍ'?'tag-baj':'tag-out'}">Ppto aceptado: ${proj.presupuesto_deco_aceptado||'—'}</span>
        <span class="tag ${proj.pedidos_confirmados==='SÍ'?'tag-baj':'tag-out'}">Pedidos: ${proj.pedidos_confirmados||'—'}</span>
      </div>
    </div>` : '';

  const html = `
    <div class="modal-bg" id="modal-bg">
      <div class="modal" style="width:min(92vw,820px);max-height:90vh;display:flex;flex-direction:column;">
        <div class="modal-head">
          <div style="flex:1;min-width:0;">
            <div class="modal-title">${proj.nombre}</div>
            <div class="modal-sub" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:4px;">
              ${tagHtml(...deptTag(proj.dpto))}
              ${tagHtml(...riskTag(g?.atencion))}
              ${proj.fase?`<span class="tag tag-out" style="font-size:10px;">${proj.fase}</span>`:''}
            </div>
          </div>
          <button class="modal-close" id="modal-close">×</button>
        </div>

        <div class="modal-body" style="overflow-y:auto;flex:1;padding:0 24px 8px;">

          <!-- IDENTIDAD -->
          <div class="modal-section">
            <div class="modal-section-label">Equipo</div>
            <div>${equipoHtml || '<span style="color:var(--ink3);font-size:12px;">Sin equipo asignado</span>'}</div>
            <table style="width:100%;font-size:12.5px;border-collapse:collapse;margin-top:6px;">
              ${row2('Estado', proj.estado||'—')}
              ${row2('Constructora', proj.constructora||'—')}
            </table>
          </div>

          <!-- GLOBAL -->
          <div class="modal-section">
            <div class="modal-section-label">Global</div>
            ${g?.bloqueador?`<div style="color:var(--crit);font-size:12.5px;font-weight:500;margin-bottom:8px;">⚠ ${g.bloqueador}</div>`:''}
            <table style="width:100%;font-size:12.5px;border-collapse:collapse;">
              ${row2('Próximo hito', g?.proximo_hito||'—')}
              ${row2('Fecha hito',   g?.fecha_hito||'—')}
              ${g?.obs?row2('Observaciones', g.obs):''}
            </table>
          </div>

          <!-- DECO -->
          ${decoHtml}

          <!-- FECHAS -->
          <div class="modal-section">
            <div class="modal-section-label">Fechas</div>
            <table style="width:100%;font-size:12.5px;border-collapse:collapse;">
              ${row2('Fin obra',     proj.fin_obra||'—')}
              ${row2('Montaje',      proj.montaje||'—')}
              ${row2('Fin oficial',  proj.fin_oficial||'—')}
            </table>
          </div>

          <!-- PLANNING -->
          <div class="modal-section" id="modal-planning-section">
            <div class="modal-section-label">Planning</div>
            <div style="margin-bottom:10px;">${ganttGeneral(proj)}</div>
            <button class="btn-primary" id="btn-planning-completo"
                    style="font-size:12px;padding:8px 18px;letter-spacing:.06em;">
              VER PLANNING COMPLETO →
            </button>
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

  // VER PLANNING COMPLETO → abre modal secundario de ancho máximo
  document.getElementById('btn-planning-completo')?.addEventListener('click', () => {
    openPlanningModal(proj);
  });
}

function closeModal() {
  document.getElementById('modal-bg')?.remove();
  document.getElementById('planning-modal-bg')?.remove();
  _modalId = null;
}

/* ── Modal de planning completo (pantalla grande) ─────────── */
function openPlanningModal(proj) {
  const g    = proj._g;
  const html = `
    <div id="planning-modal-bg" style="
      position:fixed;inset:0;z-index:1100;
      background:rgba(0,0,0,.72);
      display:flex;align-items:center;justify-content:center;
      padding:20px;">
      <div style="
        background:var(--paper);
        border-radius:8px;
        width:min(96vw,1200px);
        max-height:88vh;
        display:flex;flex-direction:column;
        box-shadow:0 20px 60px rgba(0,0,0,.4);">
        <div style="
          display:flex;align-items:center;justify-content:space-between;
          padding:18px 24px 14px;
          border-bottom:1px solid var(--line);">
          <div>
            <div style="font-size:13px;font-weight:700;letter-spacing:.04em;">${proj.nombre}</div>
            <div style="font-size:11px;color:var(--ink3);margin-top:2px;">
              Planning completo
              ${proj.fin_obra||proj.montaje ? '· Horizonte hasta '+(proj.montaje||proj.fin_obra) : ''}
            </div>
          </div>
          <button id="planning-modal-close" style="
            background:none;border:none;cursor:pointer;
            font-size:22px;color:var(--ink2);padding:4px 10px;line-height:1;">×</button>
        </div>
        <div style="overflow:auto;flex:1;padding:18px 24px 20px;">
          ${ganttCompleto(proj)}
          ${_planningLegend()}
        </div>
        <div style="
          padding:12px 24px;border-top:1px solid var(--line);
          display:flex;justify-content:flex-end;">
          <button id="planning-modal-close2" class="btn-ghost" style="font-size:11px;">Cerrar</button>
        </div>
      </div>
    </div>`;

  document.getElementById('planning-modal-bg')?.remove();
  document.body.insertAdjacentHTML('beforeend', html);

  const close = () => document.getElementById('planning-modal-bg')?.remove();
  document.getElementById('planning-modal-close')?.addEventListener('click', close);
  document.getElementById('planning-modal-close2')?.addEventListener('click', close);
  document.getElementById('planning-modal-bg')?.addEventListener('click', e => {
    if (e.target.id === 'planning-modal-bg') close();
  });
}

function _planningLegend() {
  const items = [
    ['ph1','Proyecto/Diseño'],
    ['ph2','Obra'],
    ['ph3','Montaje'],
    ['ph4','Entrega'],
    ['ph5','Renders'],
    ['ph6','Visita'],
    ['ph7','Pedidos'],
    ['ph9','Parada/Espera'],
  ];
  return `<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:14px;">
    ${items.map(([cls,lbl]) =>
      `<div style="display:flex;align-items:center;gap:5px;">
         <div class="gantt-cell ${cls} filled" style="width:18px;height:14px;border-radius:2px;"></div>
         <span style="font-size:10px;color:var(--ink3);">${lbl}</span>
       </div>`
    ).join('')}
  </div>`;
}

/* ── Agrupación de personas por departamento ─────────────── */
// Orden manual dentro de cada grupo (los primeros en la lista ocupan posición 0, 1, 2…)
const ORDEN_MANUAL = {
  'HOTELES':      ['Marta'],
  'RESTAURANTES': ['Sofía'],
  'VIVIENDA':     ['Olatz','Andrea','Sara','Nela','Cristina'],
  'SIN ASIGNAR':  []
};

function getPersonasByGroup() {
  const personas = getPersonas();

  function primaryDept(nombre) {
    const counts = { HOTELES: 0, RESTAURANTES: 0, VIVIENDA: 0 };
    (MASTER_DATA||[]).forEach(p => {
      if (!(p.equipo||[]).includes(nombre)) return;
      const d = (p.dpto||'').toUpperCase();
      if (d.includes('HOTEL'))        counts.HOTELES++;
      else if (d.includes('RESTAURANTE')) counts.RESTAURANTES++;
      else if (d.includes('VIVIENDA'))    counts.VIVIENDA++;
    });
    for (const dept of ['HOTELES','RESTAURANTES','VIVIENDA']) {
      if (counts[dept] > 0 &&
          counts[dept] === Math.max(...Object.values(counts))) return dept;
    }
    // tie-break: HOTELES > RESTAURANTES > VIVIENDA
    if (counts.HOTELES >= counts.RESTAURANTES && counts.HOTELES >= counts.VIVIENDA && counts.HOTELES > 0) return 'HOTELES';
    if (counts.RESTAURANTES >= counts.VIVIENDA && counts.RESTAURANTES > 0) return 'RESTAURANTES';
    if (counts.VIVIENDA > 0) return 'VIVIENDA';
    return 'SIN ASIGNAR';
  }

  const DEPTS  = ['HOTELES','RESTAURANTES','VIVIENDA','SIN ASIGNAR'];
  const groups = {};
  DEPTS.forEach(d => { groups[d] = []; });
  personas.forEach(n => { groups[primaryDept(n)].push(n); });

  // Ordenar cada grupo: primero el orden manual, luego el resto alfabético
  DEPTS.forEach(dept => {
    const manual = (ORDEN_MANUAL[dept]||[]).filter(n => groups[dept].includes(n));
    const resto  = groups[dept].filter(n => !manual.includes(n)).sort();
    groups[dept] = [...manual, ...resto];
  });

  return { groups, order: DEPTS };
}

/* ── CSS de grupos de pestañas ───────────────────────────── */
const GROUP_STYLES = {
  'HOTELES':      { bg: 'var(--hot)',  label: 'HOTELES' },
  'RESTAURANTES': { bg: 'var(--rest)', label: 'REST' },
  'VIVIENDA':     { bg: 'var(--viv)',  label: 'VIV' },
  'SIN ASIGNAR':  { bg: 'var(--cop)', label: '—' },
};

/* ── Tabs ─────────────────────────────────────────────────── */
let curTab = 'javi';

function buildTabs() {
  const tabsEl = document.getElementById('tabs');
  if (!tabsEl) return;
  const { groups, order } = getPersonasByGroup();

  let html = '';

  // Pestañas fijas
  html += `<button class="tab tab-master${curTab==='javi'?' active':''}" data-tab="javi">JAVI</button>`;
  html += `<button class="tab${curTab==='alejandra'?' active':''}" data-tab="alejandra">ALEJANDRA</button>`;

  // Separador visual
  html += `<div style="width:1px;background:var(--line);margin:4px 2px;align-self:stretch;opacity:.4;"></div>`;

  // Grupos de personas
  order.forEach(dept => {
    const people = groups[dept];
    if (!people.length) return;
    const st = GROUP_STYLES[dept] || {};

    // Banda de fondo para el grupo
    html += `<div class="tab-group" style="
      display:flex;align-items:center;gap:2px;
      background:color-mix(in srgb,${st.bg} 12%,transparent);
      border-radius:6px;padding:2px 4px;">`;

    people.forEach(nombre => {
      const slug = nombre.toLowerCase().replace(/\s+/g,'_');
      const id   = `p__${slug}`;
      html += `<button class="tab${curTab===id?' active':''}" data-tab="${id}"
                       style="white-space:nowrap;">${nombre}</button>`;
    });
    html += `</div>`;
  });

  tabsEl.innerHTML = html;
}

function activateTab(id) {
  curTab = id;
  document.querySelectorAll('#tabs .tab').forEach(b =>
    b.classList.toggle('active', b.dataset.tab === id));

  if      (id === 'javi')      renderJavi();
  else if (id === 'alejandra') renderAlejandra();
  else if (id.startsWith('p__')) {
    const slug   = id.slice(3);
    const nombre = getPersonas().find(n => n.toLowerCase().replace(/\s+/g,'_') === slug);
    if (nombre) renderPersona(nombre);
  }
}

/* ── Render Javi — CENTRO DE CONTROL ──────────────────────── */
function renderJavi() {
  const todos = (MASTER_DATA||[]).map(enrich);
  const sem   = hoySemana();

  const GRUPOS = [
    { level:0, label:'● ALERTA',        cls:'tag-crit', withGantt:true  },
    { level:1, label:'● ATENCIÓN',      cls:'tag-alto', withGantt:true  },
    { level:2, label:'● INFO FALTANTE', cls:'tag-med',  withGantt:false },
    { level:3, label:'● CONTROLADO',    cls:'tag-baj',  withGantt:false },
  ];

  GRUPOS.forEach(g => { g.projs = todos.filter(p => atLevel(p) === g.level); });

  let html = `<div class="view-head">
    <div>
      <div class="view-title">CENTRO DE CONTROL</div>
      <div class="view-sub">${sem} · ${todos.length} proyectos</div>
    </div>
  </div>`;

  GRUPOS.forEach(g => {
    if (!g.projs.length) return;
    html += `<div class="panel panel-${g.level===0?'alerta':g.level===1?'atencion':'default'}">
      <div class="panel-head">
        <span class="eyebrow">${tagHtml(g.cls, g.label)}&ensp;<span style="font-weight:300;color:var(--ink3);">${g.projs.length}</span></span>
      </div>
      ${g.projs.map(p => projCard(p, {gantt: g.withGantt})).join('')}
    </div>`;
  });

  document.getElementById('view').innerHTML = html;
}

/* ── Render Alejandra — DIRECCIÓN ─────────────────────────── */
function renderAlejandra() {
  const todos = (MASTER_DATA||[]).map(enrich);
  const sem   = hoySemana();

  const alerta   = todos.filter(p => atLevel(p) === 0);
  const atencion = todos.filter(p => atLevel(p) === 1);

  // ESTA SEMANA: solo proyectos en ALERTA/ATENCIÓN con actividad esta semana
  // + proyectos que no están en ALERTA/ATENCIÓN pero sí tienen actividad esta semana
  // Máximo 8 para mantener la portada limpia
  const estaSemanaAlert = todos.filter(p => atLevel(p) <= 1 && projHasActivityThisWeek(p));
  const estaSemanaNormal = todos.filter(p => atLevel(p) > 1 && projHasActivityThisWeek(p));
  // Mostramos solo los que tienen hito próximo entre los normales (máx 6)
  const estaSemanaShow = [
    ...estaSemanaAlert,
    ...estaSemanaNormal
      .filter(p => p._g?.fecha_hito)
      .sort((a,b) => (a._g.fecha_hito < b._g.fecha_hito ? -1 : 1))
      .slice(0, 6)
  ];

  // PRÓXIMAMENTE: solo hitos en las próximas 3 semanas
  const allSems  = PLANNING_DATA?.semanas || [];
  const hoyIdx   = allSems.indexOf(sem);
  const proxSems = hoyIdx >= 0 ? allSems.slice(hoyIdx + 1, hoyIdx + 4) : [];

  const proximamente = todos
    .filter(p => {
      if (!p._g?.fecha_hito) return false;
      // Fecha de hito debe estar dentro de las próximas ~3 semanas (aprox. 21 días)
      const fh = p._g.fecha_hito; // formato "DD/MM/YYYY" o ISO
      return true; // se filtra por actividad en planning, más fiable
    })
    .filter(p => projHasActivityInWindow(p, 1, 3))
    .sort((a,b) => {
      const da = a._g?.fecha_hito||'', db = b._g?.fecha_hito||'';
      return da < db ? -1 : da > db ? 1 : 0;
    });

  let html = `<div class="view-head">
    <div>
      <div class="view-title">DIRECCIÓN</div>
      <div class="view-sub">${sem}</div>
    </div>
  </div>`;

  // ALERTA
  html += `<div class="panel panel-alerta">
    <div class="panel-head">${tagHtml('tag-crit','● ALERTA')}</div>
    ${alerta.length
      ? alerta.map(p => projCard(p,{gantt:false})).join('')
      : '<p class="panel-note">Sin proyectos en alerta.</p>'}
  </div>`;

  // ATENCIÓN
  html += `<div class="panel panel-atencion">
    <div class="panel-head">${tagHtml('tag-alto','● ATENCIÓN')}</div>
    ${atencion.length
      ? atencion.map(p => projCard(p,{gantt:false})).join('')
      : '<p class="panel-note">Sin alertas de atención.</p>'}
  </div>`;

  // ESTA SEMANA (tabla)
  if (estaSemanaShow.length) {
    html += `<div class="panel">
      <div class="panel-head"><span class="eyebrow">ESTA SEMANA</span></div>
      <div class="tbl-wrap"><table class="tbl">
        <thead><tr><th>Proyecto</th><th>Dpto</th><th>Actividad</th><th>Próximo hito</th><th>Fecha</th></tr></thead>
        <tbody>
          ${estaSemanaShow.map(p => {
            const entry = (p._p?.timeline||[]).find(t => t.semana === sem);
            const act   = (entry?.actividades||[]).map(a=>a.texto).join(', ') || '—';
            return `<tr style="cursor:pointer;" data-open="${p.id}">
              <td><strong>${p.nombre}</strong></td>
              <td>${tagHtml(...deptTag(p.dpto))}</td>
              <td style="color:var(--ink2);">${act}</td>
              <td style="color:var(--ink2);">${p._g?.proximo_hito||'—'}</td>
              <td style="color:var(--cop);">${p._g?.fecha_hito||'—'}</td>
            </tr>`;
          }).join('')}
        </tbody>
      </table></div>
    </div>`;
  }

  // PRÓXIMAMENTE (solo 3 semanas vista)
  if (proximamente.length) {
    html += `<div class="panel">
      <div class="panel-head"><span class="eyebrow">PRÓXIMAMENTE</span></div>
      <div class="tbl-wrap"><table class="tbl">
        <thead><tr><th>Proyecto</th><th>Dpto</th><th>Hito</th><th>Fecha</th></tr></thead>
        <tbody>
          ${proximamente.map(p => `<tr style="cursor:pointer;" data-open="${p.id}">
            <td><strong>${p.nombre}</strong></td>
            <td>${tagHtml(...deptTag(p.dpto))}</td>
            <td style="color:var(--ink2);">${p._g?.proximo_hito||'—'}</td>
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

  // 1. PRIORIDAD: atLevel ≤ 1, ordenados por nivel
  const prioridad = todos.filter(p => atLevel(p) <= 1).sort((a,b) => atLevel(a) - atLevel(b));
  const prioIds   = new Set(prioridad.map(p => p.id));

  // 2. ESTA SEMANA: actividad esta semana, no en PRIORIDAD
  const estaSemana = todos.filter(p => !prioIds.has(p.id) && projHasActivityThisWeek(p));
  const estaIds    = new Set(estaSemana.map(p => p.id));

  // 3. OTROS PROYECTOS: el resto (incluye próximas semanas, sin actividad, etc.)
  const otrosProyectos = todos.filter(p => !prioIds.has(p.id) && !estaIds.has(p.id));

  // Índice rápido de anclaje
  const anchors = [
    prioridad.length     ? 'PRIORIDAD'      : null,
    estaSemana.length    ? 'ESTA SEMANA'    : null,
    otrosProyectos.length? 'OTROS PROYECTOS': null,
  ].filter(Boolean);

  const indiceHtml = anchors.length > 1
    ? `<div style="font-size:10.5px;letter-spacing:.08em;color:var(--ink3);margin-bottom:16px;display:flex;gap:14px;flex-wrap:wrap;">
        ${anchors.map(a => `<a href="#sec-${a.replace(/ /g,'-')}"
          style="color:var(--cop);text-decoration:none;font-weight:600;">${a}</a>`).join(' · ')}
      </div>`
    : '';

  let html = `<div class="view-head">
    <div>
      <div class="view-title">${nombre}</div>
      <div class="view-sub">${todos.length} proyecto${todos.length!==1?'s':''}</div>
    </div>
  </div>
  ${indiceHtml}`;

  if (prioridad.length) {
    html += `<div id="sec-PRIORIDAD" class="panel panel-alerta">
      <div class="panel-head">${tagHtml('tag-crit','● PRIORIDAD')}&ensp;<span class="eyebrow" style="font-weight:300;">${prioridad.length}</span></div>
      ${prioridad.map(p => projCard(p, {gantt:false})).join('')}
    </div>`;
  }

  if (estaSemana.length) {
    html += `<div id="sec-ESTA-SEMANA" class="panel panel-semana">
      <div class="panel-head"><span class="eyebrow">ESTA SEMANA · ${sem}</span></div>
      ${estaSemana.map(p => projCard(p, {gantt:true})).join('')}
    </div>`;
  }

  if (otrosProyectos.length) {
    html += `<div id="sec-OTROS-PROYECTOS" class="panel panel-otros">
      <div class="panel-head"><span class="eyebrow">OTROS PROYECTOS · ${otrosProyectos.length}</span></div>
      ${otrosProyectos.map(p => projCard(p, {gantt:false})).join('')}
    </div>`;
  }

  if (!todos.length) {
    html += '<p class="panel-note" style="margin-top:20px;">Sin proyectos asignados.</p>';
  }

  document.getElementById('view').innerHTML = html;
}

/* ── Exportar ─────────────────────────────────────────────── */
function exportar() {
  const hoy  = new Date().toLocaleDateString('es-ES');
  const sem  = hoySemana();
  const lines = [`POMBO ESTUDIO — ${hoy} (${sem})`, '='.repeat(50), ''];

  ['VIVIENDA','RESTAURANTES','HOTELES'].forEach(dpto => {
    const ps = (MASTER_DATA||[]).filter(p => (p.dpto||'').toUpperCase().includes(dpto.slice(0,-1)||dpto));
    if (!ps.length) return;
    lines.push(`\n── ${dpto} (${ps.length}) ──`);
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

/* ── CSS dinámico para estilos de panel y tabs ────────────── */
function injectStyles() {
  const css = `
    .panel-alerta  { border-left: 3px solid var(--crit); }
    .panel-atencion{ border-left: 3px solid var(--alto,#c47a2a); }
    .panel-semana  { border-left: 3px solid var(--cop); }
    .panel-otros   { border-left: 3px solid var(--line); }
    .tab-group     { display:inline-flex; }
    .modal-section { margin-bottom:16px; padding-bottom:14px; border-bottom:1px solid var(--line); }
    .modal-section:last-child { border-bottom:none; }
    .modal-section-label {
      font-size:9.5px;font-weight:700;letter-spacing:.1em;
      text-transform:uppercase;color:var(--ink3);margin-bottom:8px;
    }
    .panel-note { font-size:12px;color:var(--ink3);padding:8px 0; }
  `;
  const el = document.createElement('style');
  el.textContent = css;
  document.head.appendChild(el);
}

/* ── Eventos ──────────────────────────────────────────────── */
function wireEvents() {
  document.getElementById('tabs')?.addEventListener('click', e => {
    const b = e.target.closest('.tab');
    if (b) activateTab(b.dataset.tab);
  });

  document.getElementById('view')?.addEventListener('click', e => {
    const open = e.target.closest('[data-open]');
    if (open) { openModal(open.dataset.open); return; }
  });

  document.getElementById('export-btn')?.addEventListener('click', exportar);
  document.addEventListener('keydown', e => { if (e.key==='Escape') closeModal(); });
}

/* ── Init ─────────────────────────────────────────────────── */
function init() {
  injectStyles();
  buildIndexes();
  buildTabs();
  wireEvents();
  activateTab('javi');

  const wb = document.getElementById('week-badge');
  if (wb) wb.textContent = hoySemana();

  const ub = document.getElementById('update-badge');
  if (ub && META?.updated) ub.textContent = 'Act. ' + META.updated.replace('T',' ').slice(0,16);
}

document.addEventListener('DOMContentLoaded', init);
