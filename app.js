/* ============================================================
   POMBO ESTUDIO — app.js
   Usa MASTER_DATA, GLOBAL_DATA, PLANNING_DATA, META
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
// META.hoy_semana es el label string de la semana actual (p.ej. "5 OCT")
const hoySemana = () => META?.hoy_semana || '';
const VENTANA   = 6; // semanas hacia adelante en la tarjeta

function semanaWindow() {
  const sems = PLANNING_DATA?.semanas || [];
  const i    = sems.indexOf(hoySemana());
  if (i < 0) return sems.slice(0, VENTANA);
  return sems.slice(i, i + VENTANA);
}

/* ── Personas ─────────────────────────────────────────────── */
// Javier, Alejandra y Alicia no aparecen en las pestañas del equipo
const EXCLUIR_PERSONAS = ['Alicia', 'Javier', 'Alejandra', 'Javi', 'alicia'];

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
function atLevel(proj) {
  const a = (proj._g?.atencion || proj.atencion || '').toUpperCase();
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
  if (t.includes('ANTEPR'))  return 'APY';
  if (t.includes('PROY'))    return 'PRY';
  if (t.includes('VALORAC')) return 'VAL';
  if (t.includes('OBRA'))    return 'OBR';
  if (t.includes('MONTAJ'))  return 'MNT';
  if (t.includes('ENTREGA')) return 'ENT';
  if (t.includes('RENDER'))  return 'RND';
  if (t.includes('VISITA'))  return 'VIS';
  if (t.includes('PEDIDO'))  return 'PED';
  if (t.includes('REMATE'))  return 'REM';
  if (t.includes('PARAD') || t.includes('ESPERA') || t.includes('STANDBY')) return '···';
  return txt.slice(0,3).toUpperCase();
}

// Colores coherentes con PLANNING_POMBO
function faseColor(txt) {
  const t = (txt||'').toUpperCase();
  if (t.includes('ANTEPR'))  return 'ph1';
  if (t.includes('PROY') || t.includes('DISEÑO') || t.includes('VALORAC')) return 'ph1';
  if (t.includes('OBRA'))    return 'ph2';
  if (t.includes('MONTAJ'))  return 'ph3';
  if (t.includes('ENTREGA')) return 'ph4';
  if (t.includes('RENDER'))  return 'ph5';
  if (t.includes('VISITA'))  return 'ph6';
  if (t.includes('PEDIDO') || t.includes('REMATE')) return 'ph7';
  if (t.includes('PARAD') || t.includes('ESPERA') || t.includes('STANDBY')) return 'ph9';
  return 'ph1';
}

function row2(k, v) {
  if (!v || v === '—' || v === 'None') return '';
  return `<tr>
    <td style="color:var(--ink3);font-size:10px;letter-spacing:.08em;text-transform:uppercase;
               padding:4px 0;width:130px;vertical-align:top;">${k}</td>
    <td style="padding:4px 0;font-size:12.5px;">${v}</td>
  </tr>`;
}

function row2Always(k, v) {
  return `<tr>
    <td style="color:var(--ink3);font-size:10px;letter-spacing:.08em;text-transform:uppercase;
               padding:4px 0;width:130px;vertical-align:top;">${k}</td>
    <td style="padding:4px 0;font-size:12.5px;color:${(!v||v==='—')?'var(--ink3)':'inherit'};">${v||'Sin fecha registrada'}</td>
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

/* ── Gantt tarjeta (ventana operativa compacta) ──────────── */
function ganttGeneral(proj) {
  const ventana = semanaWindow();
  const hoy     = hoySemana();
  if (!ventana.length) return '';

  let weeksHtml = '<div class="gantt-weeks">';
  ventana.forEach(sem => {
    const isHoy = sem === hoy;
    weeksHtml += `<div class="gantt-week${isHoy?' gantt-week-hoy':''}" style="font-size:9px;">${sem}</div>`;
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

/* ── Gantt completo (en el modal) ────────────────────────── */
function ganttCompleto(proj) {
  const sems = PLANNING_DATA?.semanas || [];
  const hoy  = hoySemana();
  if (!sems.length) return '<p style="color:var(--ink3);font-size:12px;">Sin datos de planning.</p>';

  const N = sems.length;
  const colW = `repeat(${N},minmax(28px,1fr))`;

  let weeksHtml = `<div style="display:grid;grid-template-columns:${colW};gap:1px;margin-bottom:2px;">`;
  sems.forEach(sem => {
    const isHoy = sem === hoy;
    weeksHtml += `<div style="font-size:8.5px;font-weight:${isHoy?700:500};letter-spacing:.02em;
      text-align:center;padding:3px 1px;
      color:${isHoy?'var(--burg)':'var(--ink3)'};
      border-bottom:${isHoy?'2px solid var(--burg)':'1px solid transparent'};">${sem}</div>`;
  });
  weeksHtml += '</div>';

  let cellsHtml = `<div style="display:grid;grid-template-columns:${colW};gap:1px;">`;
  sems.forEach(sem => {
    const entry = (proj._p?.timeline||[]).find(t => t.semana === sem);
    const texto = entry?.actividades?.[0]?.texto || '';
    const ph    = texto ? faseColor(texto) : '';
    const cls   = `gantt-cell${ph?' '+ph+' filled':''}${sem===hoy?' gantt-cell-hoy':''}`;
    cellsHtml  += `<div class="${cls}" title="${sem}${texto?': '+texto:''}"
      style="height:30px;display:flex;align-items:center;justify-content:center;border-radius:3px;">
      ${texto?`<span class="gantt-label" style="font-size:8.5px;font-weight:600;">${abrev(texto)}</span>`:''}
    </div>`;
  });
  cellsHtml += '</div>';

  return `<div style="overflow-x:auto;padding-bottom:4px;">${weeksHtml}${cellsHtml}</div>`;
}

function _planningLegend() {
  const items = [
    ['ph1','Proyecto/Diseño'],['ph2','Obra'],['ph3','Montaje'],['ph4','Entrega'],
    ['ph5','Renders'],['ph6','Visita'],['ph7','Pedidos/Remates'],['ph9','Parada'],
  ];
  return `<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px;padding-top:10px;border-top:1px solid var(--line);">
    ${items.map(([cls,lbl]) =>
      `<div style="display:flex;align-items:center;gap:5px;">
         <div class="gantt-cell ${cls} filled" style="width:16px;height:12px;border-radius:2px;"></div>
         <span style="font-size:9.5px;color:var(--ink3);">${lbl}</span>
       </div>`
    ).join('')}
  </div>`;
}

/* ── Tarjeta de proyecto ─────────────────────────────────── */
function projCard(proj, opts={}) {
  const g    = proj._g;
  const [dCls, dTxt] = deptTag(proj.dpto);
  const [rCls, rTxt] = riskTag(g?.atencion || proj.atencion);
  const hito  = g?.proximo_hito || proj.hito || '';
  const fecha = g?.fecha_hito   || proj.fecha || '';
  const bloq  = g?.bloqueador   || proj.bloqueador || '';
  const equipo = (proj.equipo||[]).filter(e => e && e.length > 1).join(' · ');

  const hitoHtml = hito && hito !== '—'
    ? `<div class="hito-row"><span class="hito-text">${hito}</span>${fecha&&fecha!=='—'?`<span class="hito-date">${fecha}</span>`:''}</div>`
    : '';
  const bloqHtml = bloq && bloq !== '—'
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
          ${proj.fase&&proj.fase!=='—'?`<span class="tag tag-out" style="font-size:10px;">${proj.fase}</span>`:''}
        </div>
        <div class="proj-name" style="cursor:pointer;" data-open="${proj.id}">${proj.nombre}</div>
      </div>
      <button class="btn-ver" data-open="${proj.id}">
        VER PROYECTO →
      </button>
    </div>
    ${hitoHtml}${bloqHtml}${equipoHtml}
    ${ganttHtml}
  </div>`;
}

/* ── Modal unificado: ficha completa + planning ──────────── */
let _modalId = null;

function openModal(id) {
  const raw = (MASTER_DATA||[]).find(p => p.id === id);
  if (!raw) return;
  _modalId = id;
  const proj = enrich(raw);
  const g    = proj._g;

  const equipoHtml = (proj.equipo||[]).filter(e => e && e.length > 1)
    .map(e => `<span class="tag tag-out">${e}</span>`).join(' ');

  // Sección DECO
  const decoItems = [
    ['Deco cerrada',     proj.deco_cerrada],
    ['Ppto. aceptado',   proj.presupuesto_deco_aceptado],
    ['Pedidos',          proj.pedidos_confirmados],
  ].filter(([,v]) => v && v !== '—' && v !== 'None');

  const decoHtml = decoItems.length ? `
    <div class="modal-section">
      <div class="modal-section-label" style="color:var(--viv-dk,#5a7a3a);">
        ▸ DECO
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        ${decoItems.map(([k,v]) =>
          `<span class="tag ${v==='SÍ'||v==='Sí'?'tag-baj':'tag-out'}">${k}: ${v}</span>`
        ).join('')}
      </div>
    </div>` : '';

  // Sección FECHAS
  const fechasHtml = `
    <div class="modal-section">
      <div class="modal-section-label">▸ FECHAS IMPORTANTES</div>
      <table style="width:100%;font-size:12.5px;border-collapse:collapse;">
        ${row2Always('Fin de obra previsto', proj.fin_obra)}
        ${row2Always('Montaje previsto',     proj.montaje)}
        ${row2Always('Fin oficial',          proj.entrega || proj.fin_oficial)}
        ${row2Always('Próximo hito',         g?.proximo_hito || proj.hito)}
        ${row2Always('Fecha del hito',       g?.fecha_hito || proj.fecha)}
      </table>
    </div>`;

  const html = `
    <div class="modal-bg" id="modal-bg">
      <div class="modal" style="width:min(95vw,1100px);max-height:92vh;display:flex;flex-direction:column;">

        <div class="modal-head">
          <div style="flex:1;min-width:0;">
            <div class="modal-title">${proj.nombre}</div>
            <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:4px;">
              ${tagHtml(...deptTag(proj.dpto))}
              ${tagHtml(...riskTag(g?.atencion||proj.atencion))}
              ${proj.fase&&proj.fase!=='—'?`<span class="tag tag-out" style="font-size:10px;">${proj.fase}</span>`:''}
            </div>
          </div>
          <button class="modal-close" id="modal-close">×</button>
        </div>

        <div class="modal-body" style="overflow-y:auto;flex:1;padding:0 24px 16px;display:grid;grid-template-columns:1fr 1fr;gap:0 24px;">

          <!-- COL IZQ -->
          <div>
            <!-- IDENTIDAD -->
            <div class="modal-section">
              <div class="modal-section-label">▸ IDENTIDAD</div>
              <div style="margin-bottom:8px;">${equipoHtml || '<span style="color:var(--ink3);font-size:12px;">Sin equipo asignado</span>'}</div>
              <table style="width:100%;font-size:12.5px;border-collapse:collapse;">
                ${row2('Estado', proj.estado)}
                ${row2('Constructora', proj.constructora)}
                ${row2('Fase', proj.fase)}
              </table>
            </div>

            <!-- ESTADO Y SEGUIMIENTO GLOBAL -->
            <div class="modal-section">
              <div class="modal-section-label">▸ SEGUIMIENTO GLOBAL</div>
              ${(g?.bloqueador&&g.bloqueador!=='—')?`<div style="color:var(--crit);font-size:12.5px;font-weight:500;margin-bottom:8px;padding:6px 8px;background:rgba(180,30,30,.06);border-radius:4px;">⚠ ${g.bloqueador}</div>`:''}
              <table style="width:100%;font-size:12.5px;border-collapse:collapse;">
                ${row2('Próximo hito',  g?.proximo_hito || proj.hito)}
                ${row2('Fecha hito',    g?.fecha_hito || proj.fecha)}
                ${row2('Fase real',     g?.fase_real)}
                ${row2('Acción',        g?.obs || proj.obs)}
                ${row2('Cuándo',        g?.cuando)}
              </table>
            </div>

            <!-- DECO -->
            ${decoHtml}

            <!-- FECHAS -->
            ${fechasHtml}
          </div>

          <!-- COL DER: PLANNING COMPLETO -->
          <div style="border-left:1px solid var(--line);padding-left:20px;">
            <div class="modal-section" style="border-bottom:none;height:100%;">
              <div class="modal-section-label">▸ PLANNING COMPLETO</div>
              ${ganttCompleto(proj)}
              ${_planningLegend()}
            </div>
          </div>

        </div>

        <div class="modal-foot">
          <button class="btn-ghost" id="modal-close2">Cerrar</button>
        </div>
      </div>
    </div>`;

  document.getElementById('modal-bg')?.remove();
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('modal-close')?.addEventListener('click',  closeModal);
  document.getElementById('modal-close2')?.addEventListener('click', closeModal);
  document.getElementById('modal-bg')?.addEventListener('click', e => {
    if (e.target.id === 'modal-bg') closeModal();
  });
}

function closeModal() {
  document.getElementById('modal-bg')?.remove();
  _modalId = null;
}

/* ── Agrupación de personas por departamento ─────────────── */
const ORDEN_MANUAL = {
  'HOTELES':      ['Marta','Naiara'],
  'RESTAURANTES': ['Sofía','Sofia'],
  'VIVIENDA':     ['Olatz','Andrea','Sara','Nela','Cristina','Paula'],
  'SIN ASIGNAR':  []
};

function getPersonasByGroup() {
  const personas = getPersonas();

  function primaryDept(nombre) {
    const counts = { HOTELES: 0, RESTAURANTES: 0, VIVIENDA: 0 };
    (MASTER_DATA||[]).forEach(p => {
      if (!(p.equipo||[]).includes(nombre)) return;
      const d = (p.dpto||'').toUpperCase();
      if (d.includes('HOTEL'))             counts.HOTELES++;
      else if (d.includes('RESTAURANTE'))  counts.RESTAURANTES++;
      else if (d.includes('VIVIENDA'))     counts.VIVIENDA++;
    });
    for (const dept of ['HOTELES','RESTAURANTES','VIVIENDA']) {
      if (counts[dept] > 0 && counts[dept] === Math.max(...Object.values(counts))) return dept;
    }
    if (counts.HOTELES > 0)      return 'HOTELES';
    if (counts.RESTAURANTES > 0) return 'RESTAURANTES';
    if (counts.VIVIENDA > 0)     return 'VIVIENDA';
    return 'SIN ASIGNAR';
  }

  const DEPTS  = ['HOTELES','RESTAURANTES','VIVIENDA','SIN ASIGNAR'];
  const groups = {};
  DEPTS.forEach(d => { groups[d] = []; });
  personas.forEach(n => { groups[primaryDept(n)].push(n); });

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
// Orden: ALEJANDRA primero, JAVIER segundo, luego grupos por dept
let curTab = 'alejandra';

function buildTabs() {
  const tabsEl = document.getElementById('tabs');
  if (!tabsEl) return;
  const { groups, order } = getPersonasByGroup();

  let html = '';

  // Pestañas fijas: ALEJANDRA · DIRECCIÓN primero, JAVIER · CENTRO DE CONTROL segundo
  html += `<button class="tab${curTab==='alejandra'?' active':''}" data-tab="alejandra"
            style="font-weight:600;">ALEJANDRA · DIRECCIÓN</button>`;
  html += `<button class="tab tab-master${curTab==='javi'?' active':''}" data-tab="javi"
            style="font-weight:600;">JAVIER · CENTRO DE CONTROL</button>`;

  // Separador
  html += `<div style="width:1px;background:var(--line);margin:4px 4px;align-self:stretch;opacity:.4;"></div>`;

  // Grupos por departamento (HOTELES, REST, VIV)
  order.forEach(dept => {
    const people = groups[dept];
    if (!people.length) return;
    const st = GROUP_STYLES[dept] || {};

    html += `<div class="tab-group" style="
      display:flex;align-items:center;gap:2px;
      background:color-mix(in srgb,${st.bg} 18%,transparent);
      border-radius:6px;padding:2px 6px;
      border:1px solid color-mix(in srgb,${st.bg} 30%,transparent);">`;

    people.forEach(nombre => {
      const slug = nombre.toLowerCase().replace(/\s+/g,'_').replace(/[áa]/g,'a').replace(/[éeê]/g,'e');
      const id   = `p__${slug}`;
      html += `<button class="tab${curTab===id?' active':''}" data-tab="${id}"
               style="white-space:nowrap;font-size:11px;">${nombre}</button>`;
    });
    html += `</div>`;
  });

  tabsEl.innerHTML = html;
}

function activateTab(id) {
  curTab = id;
  document.querySelectorAll('#tabs .tab').forEach(b =>
    b.classList.toggle('active', b.dataset.tab === id));

  if      (id === 'alejandra') renderAlejandra();
  else if (id === 'javi')      renderJavi();
  else if (id.startsWith('p__')) {
    const slug   = id.slice(3);
    // Buscar la persona cuyo slug coincida
    const nombre = getPersonas().find(n => {
      const ns = n.toLowerCase().replace(/\s+/g,'_').replace(/[áa]/g,'a').replace(/[éeê]/g,'e');
      return ns === slug;
    });
    if (nombre) renderPersona(nombre);
  }
}

/* ── COLORES DE BLOQUES para índices ────────────────────────
   Deben coincidir con los fondos de los paneles.
   ──────────────────────────────────────────────────────────*/
const BG_ALERTA    = 'rgba(180,30,30,.08)';
const BG_ATENCION  = 'rgba(196,122,42,.07)';
const BG_INFO      = 'rgba(80,80,140,.05)';
const BG_CONTROLADO= 'rgba(0,0,0,.03)';
const BG_SEMANA    = 'rgba(42,100,140,.06)';
const BG_PROX      = 'rgba(42,120,80,.05)';
const BG_OTROS     = 'rgba(0,0,0,.02)';

const BORDE_ALERTA    = '#b41e1e';
const BORDE_ATENCION  = '#c47a2a';
const BORDE_INFO      = '#50508c';
const BORDE_CONTROLADO= '#aaaaaa';
const BORDE_SEMANA    = '#2a648c';
const BORDE_PROX      = '#2a7850';
const BORDE_OTROS     = '#cccccc';

function indexBtn(id, label, bg, borde, count) {
  if (!count) return '';
  return `<a href="#${id}" class="idx-btn"
    style="background:${bg};border:1px solid ${borde};color:${borde};">
    ${label} <span style="font-weight:300;opacity:.7;">${count}</span>
  </a>`;
}

/* ── Render Alejandra — DIRECCIÓN ─────────────────────────── */
function renderAlejandra() {
  const todos = (MASTER_DATA||[]).map(enrich);
  const sem   = hoySemana();

  const alerta   = todos.filter(p => atLevel(p) === 0);
  const atencion = todos.filter(p => atLevel(p) === 1);

  const estaSemanaAlert  = todos.filter(p => atLevel(p) <= 1 && projHasActivityThisWeek(p));
  const estaSemanaNormal = todos.filter(p => atLevel(p) > 1  && projHasActivityThisWeek(p));
  const estaSemana = [...estaSemanaAlert, ...estaSemanaNormal];

  const proximamente = todos
    .filter(p => projHasActivityInWindow(p, 1, 3))
    .sort((a,b) => {
      const da = a._g?.fecha_hito||'', db = b._g?.fecha_hito||'';
      return da < db ? -1 : da > db ? 1 : 0;
    });

  // Índice
  const indiceHtml = `
    <div class="idx-nav" style="margin-bottom:20px;">
      ${indexBtn('ale-alerta',    '● ALERTA',      BG_ALERTA,    BORDE_ALERTA,    alerta.length)}
      ${indexBtn('ale-atencion',  '● ATENCIÓN',    BG_ATENCION,  BORDE_ATENCION,  atencion.length)}
      ${indexBtn('ale-semana',    'ESTA SEMANA',   BG_SEMANA,    BORDE_SEMANA,    estaSemana.length)}
      ${indexBtn('ale-prox',      'PRÓXIMAMENTE',  BG_PROX,      BORDE_PROX,      proximamente.length)}
    </div>`;

  let html = `<div class="view-head">
    <div>
      <div class="view-title">DIRECCIÓN</div>
      <div class="view-sub">${sem} · ${todos.length} proyectos</div>
    </div>
  </div>
  ${indiceHtml}`;

  html += `<div id="ale-alerta" class="panel" style="background:${BG_ALERTA};border-left:3px solid ${BORDE_ALERTA};">
    <div class="panel-head">${tagHtml('tag-crit','● ALERTA')}&ensp;<span style="font-weight:300;color:var(--ink3);">${alerta.length}</span></div>
    ${alerta.length ? alerta.map(p => projCard(p,{gantt:false})).join('') : '<p class="panel-note">Sin proyectos en alerta.</p>'}
  </div>`;

  html += `<div id="ale-atencion" class="panel" style="background:${BG_ATENCION};border-left:3px solid ${BORDE_ATENCION};">
    <div class="panel-head">${tagHtml('tag-alto','● ATENCIÓN')}&ensp;<span style="font-weight:300;color:var(--ink3);">${atencion.length}</span></div>
    ${atencion.length ? atencion.map(p => projCard(p,{gantt:false})).join('') : '<p class="panel-note">Sin proyectos en atención.</p>'}
  </div>`;

  if (estaSemana.length) {
    html += `<div id="ale-semana" class="panel" style="background:${BG_SEMANA};border-left:3px solid ${BORDE_SEMANA};">
      <div class="panel-head"><span class="eyebrow">ESTA SEMANA</span> <span style="font-size:11px;color:var(--ink3);font-weight:300;">${sem}</span></div>
      <div class="tbl-wrap"><table class="tbl">
        <thead><tr><th>Proyecto</th><th>Dpto</th><th>Actividad</th><th>Próximo hito</th><th>Fecha</th></tr></thead>
        <tbody>
          ${estaSemana.map(p => {
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

  if (proximamente.length) {
    html += `<div id="ale-prox" class="panel" style="background:${BG_PROX};border-left:3px solid ${BORDE_PROX};">
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

/* ── Render Javi — CENTRO DE CONTROL ──────────────────────── */
function renderJavi() {
  const todos = (MASTER_DATA||[]).map(enrich);
  const sem   = hoySemana();

  const GRUPOS = [
    { level:0, id:'javi-alerta',     label:'● ALERTA',        cls:'tag-crit', bg:BG_ALERTA,     borde:BORDE_ALERTA,    withGantt:true  },
    { level:1, id:'javi-atencion',   label:'● ATENCIÓN',      cls:'tag-alto', bg:BG_ATENCION,   borde:BORDE_ATENCION,  withGantt:true  },
    { level:2, id:'javi-info',       label:'● INFO FALTANTE', cls:'tag-med',  bg:BG_INFO,       borde:BORDE_INFO,      withGantt:false },
    { level:3, id:'javi-controlado', label:'● CONTROLADO',    cls:'tag-baj',  bg:BG_CONTROLADO, borde:BORDE_CONTROLADO,withGantt:false },
  ];

  GRUPOS.forEach(g => { g.projs = todos.filter(p => atLevel(p) === g.level); });

  const indiceHtml = `
    <div class="idx-nav" style="margin-bottom:20px;">
      ${GRUPOS.map(g => indexBtn(g.id, g.label, g.bg, g.borde, g.projs.length)).join('')}
    </div>`;

  let html = `<div class="view-head">
    <div>
      <div class="view-title">CENTRO DE CONTROL</div>
      <div class="view-sub">${sem} · ${todos.length} proyectos</div>
    </div>
  </div>
  ${indiceHtml}`;

  GRUPOS.forEach(g => {
    if (!g.projs.length) return;
    html += `<div id="${g.id}" class="panel" style="background:${g.bg};border-left:3px solid ${g.borde};">
      <div class="panel-head">
        <span class="eyebrow">${tagHtml(g.cls, g.label)}&ensp;<span style="font-weight:300;color:var(--ink3);">${g.projs.length}</span></span>
      </div>
      ${g.projs.map(p => projCard(p, {gantt: g.withGantt})).join('')}
    </div>`;
  });

  document.getElementById('view').innerHTML = html;
}

/* ── Render Persona ──────────────────────────────────────── */
function renderPersona(nombre) {
  const todos = (MASTER_DATA||[]).filter(p => (p.equipo||[]).includes(nombre)).map(enrich);
  const sem   = hoySemana();

  const prioridad      = todos.filter(p => atLevel(p) <= 1).sort((a,b) => atLevel(a)-atLevel(b));
  const prioIds        = new Set(prioridad.map(p => p.id));
  const estaSemana     = todos.filter(p => !prioIds.has(p.id) && projHasActivityThisWeek(p));
  const estaIds        = new Set(estaSemana.map(p => p.id));
  const otrosProyectos = todos.filter(p => !prioIds.has(p.id) && !estaIds.has(p.id));

  const indiceHtml = `
    <div class="idx-nav" style="margin-bottom:20px;">
      ${indexBtn('sec-PRIORIDAD',       '● PRIORIDAD',       BG_ALERTA,   BORDE_ALERTA,   prioridad.length)}
      ${indexBtn('sec-ESTA-SEMANA',     'ESTA SEMANA',       BG_SEMANA,   BORDE_SEMANA,   estaSemana.length)}
      ${indexBtn('sec-OTROS-PROYECTOS', 'OTROS PROYECTOS',   BG_OTROS,    BORDE_OTROS,    otrosProyectos.length)}
    </div>`;

  let html = `<div class="view-head">
    <div>
      <div class="view-title">${nombre}</div>
      <div class="view-sub">${todos.length} proyecto${todos.length!==1?'s':''}</div>
    </div>
  </div>
  ${indiceHtml}`;

  if (prioridad.length) {
    html += `<div id="sec-PRIORIDAD" class="panel" style="background:${BG_ALERTA};border-left:3px solid ${BORDE_ALERTA};">
      <div class="panel-head">${tagHtml('tag-crit','● PRIORIDAD')}&ensp;<span style="font-weight:300;color:var(--ink3);">${prioridad.length}</span></div>
      ${prioridad.map(p => projCard(p, {gantt:false})).join('')}
    </div>`;
  }

  if (estaSemana.length) {
    html += `<div id="sec-ESTA-SEMANA" class="panel" style="background:${BG_SEMANA};border-left:3px solid ${BORDE_SEMANA};">
      <div class="panel-head"><span class="eyebrow">ESTA SEMANA · ${sem}</span></div>
      ${estaSemana.map(p => projCard(p, {gantt:true})).join('')}
    </div>`;
  }

  if (otrosProyectos.length) {
    html += `<div id="sec-OTROS-PROYECTOS" class="panel" style="background:${BG_OTROS};border-left:3px solid ${BORDE_OTROS};">
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
  a.download = `pombo_${(sem||'export').replace('/','_')}.txt`;
  a.click();
}

/* ── CSS dinámico ─────────────────────────────────────────── */
function injectStyles() {
  const css = `
    /* Botón VER con fondo corporativo */
    .btn-ver {
      font-size:10.5px;font-weight:600;letter-spacing:.07em;
      padding:5px 12px;white-space:nowrap;flex-shrink:0;
      background:var(--burg,#4a2020);color:#fff;
      border:none;border-radius:4px;cursor:pointer;
      transition:opacity .15s;
    }
    .btn-ver:hover { opacity:.82; }

    /* Índice de navegación */
    .idx-nav {
      display:flex;flex-wrap:wrap;gap:8px;
    }
    .idx-btn {
      font-size:10.5px;font-weight:600;letter-spacing:.07em;
      padding:5px 13px;border-radius:4px;text-decoration:none;
      transition:opacity .15s;
    }
    .idx-btn:hover { opacity:.75; }

    /* Paneles */
    .panel { margin-bottom:16px;border-radius:6px;padding:14px 16px; }
    .panel-note { font-size:12px;color:var(--ink3);padding:8px 0; }

    /* Modal */
    .modal-section { margin-bottom:16px;padding-bottom:14px;border-bottom:1px solid var(--line); }
    .modal-section:last-child { border-bottom:none; }
    .modal-section-label {
      font-size:9.5px;font-weight:700;letter-spacing:.1em;
      text-transform:uppercase;color:var(--ink3);margin-bottom:8px;
    }

    /* Tab groups */
    .tab-group { display:inline-flex; }

    /* Scroll en modal en pantallas pequeñas */
    @media (max-width:780px) {
      .modal > .modal-body { grid-template-columns:1fr !important; }
      .modal > .modal-body > div:nth-child(2) { border-left:none !important; padding-left:0 !important; border-top:1px solid var(--line); padding-top:16px; }
    }
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
  activateTab('alejandra');  // Alejandra es la pestaña inicial

  const wb = document.getElementById('week-badge');
  if (wb) wb.textContent = hoySemana();

  const ub = document.getElementById('update-badge');
  if (ub && META?.updated) ub.textContent = 'Act. ' + META.updated;
}

document.addEventListener('DOMContentLoaded', init);
