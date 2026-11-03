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
  const ventana  = semanaWindow();
  const allSems  = PLANNING_DATA?.semanas || [];
  const hoy      = hoySemana();
  if (!ventana.length) return '';

  // Determinar si el proyecto está oficialmente parado
  const estadoRaw = (proj.estado || proj._g?.fase_real || proj.fase || '').toUpperCase();
  const isParado  = /PARAD|ESPERA|STANDBY|STOP|HOLD/.test(estadoRaw);

  // Rango activo en TODO el planning (no solo en la ventana)
  const timeline   = proj._p?.timeline || [];
  const activeSems = new Set(timeline.filter(t => t.actividades?.length).map(t => t.semana));
  let firstActive  = null, lastActive = null;
  allSems.forEach(sem => {
    if (activeSems.has(sem)) {
      if (!firstActive) firstActive = sem;
      lastActive = sem;
    }
  });
  // Si el proyecto no está parado, extender lastActive hasta hoy (inclusive)
  if (!isParado && lastActive) {
    const lastIdx = allSems.indexOf(lastActive);
    const hoyIdx  = allSems.indexOf(hoy);
    if (hoyIdx > lastIdx) lastActive = hoy;
  }
  const firstIdxAll = firstActive ? allSems.indexOf(firstActive) : -1;
  const lastIdxAll  = lastActive  ? allSems.indexOf(lastActive)  : -1;

  let weeksHtml = '<div class="gantt-weeks">';
  ventana.forEach(sem => {
    const isHoy = sem === hoy;
    weeksHtml += `<div class="gantt-week${isHoy?' gantt-week-hoy':''}" style="font-size:9px;">${sem}</div>`;
  });
  weeksHtml += '</div>';

  // Construir mapa semana→fase para forward-fill dentro de app.js
  // (el forward-fill entre semanas con registros ya viene de generate_app.py;
  //  aquí solo cubrimos la extensión desde lastActive hasta hoy)
  const textoMap = {};
  let lastKnownTexto = '';
  allSems.forEach(sem => {
    const entry = timeline.find(t => t.semana === sem);
    const t = entry?.actividades?.[0]?.texto || '';
    if (t) lastKnownTexto = t;
    textoMap[sem] = t;
  });

  let cellsHtml = '<div class="gantt-grid">';
  ventana.forEach(sem => {
    const semIdx = allSems.indexOf(sem);
    const inRange = firstIdxAll >= 0 && lastIdxAll >= 0
                    && semIdx >= firstIdxAll && semIdx <= lastIdxAll;
    const registrado = textoMap[sem] || '';
    // Para semanas vacías dentro del rango activo (incluida la extensión a hoy):
    // usar la última fase conocida del proyecto (forward-fill), no ph-pending
    let texto = registrado;
    let isFilled = false;
    if (!texto && !isParado && inRange) {
      // Encontrar la última fase registrada hasta esta semana
      let fill = '';
      for (let i = firstIdxAll; i <= semIdx; i++) {
        const s = allSems[i];
        if (textoMap[s]) fill = textoMap[s];
      }
      if (fill) { texto = fill; isFilled = true; }
    }
    const ph  = texto ? faseColor(texto) : '';
    const isParadaCell = !registrado && isParado && inRange;
    const cls = `gantt-cell${ph?' '+ph+' filled':''}${isFilled?' ph-continuidad':''}${isParadaCell?' ph9 filled':''}${sem===hoy?' gantt-cell-hoy':''}`;
    const title = `${sem}${registrado?': '+registrado:isFilled?': '+texto+' (continuidad de fase)':isParadaCell?' (proyecto parado)':''}`;
    const label = registrado ? abrev(registrado) : isParadaCell ? '···' : isFilled ? abrev(texto) : '';
    cellsHtml += `<div class="${cls}" title="${title}">${label?`<span class="gantt-label">${label}</span>`:''}</div>`;
  });
  cellsHtml += '</div>';

  return `<div class="gantt" style="overflow-x:auto;">${weeksHtml}${cellsHtml}</div>`;
}

/* ── Gantt completo (en el modal) ────────────────────────── */

/* Parsea etiquetas de fecha del Master como "30 oct'26", "Dic'26", "Ene'27", "TBD", "—"
   Devuelve un Date o null. */
function _parseFechaProyecto(str) {
  if (!str || str === '—' || str.toLowerCase() === 'tbd') return null;
  const MESES = {ene:0,feb:1,mar:2,abr:3,may:4,jun:5,jul:6,ago:7,sep:8,oct:9,nov:10,dic:11};
  // "30 oct'26" → día 30, oct, 2026
  let m = str.match(/(\d{1,2})\s+([a-záéíóú]{3})'(\d{2})/i);
  if (m) {
    const mes = MESES[m[2].toLowerCase()];
    if (mes !== undefined) return new Date(2000 + parseInt(m[3]), mes, parseInt(m[1]));
  }
  // "Dic'26" → día 1, dic, 2026
  m = str.match(/([a-záéíóú]{3})'(\d{2})/i);
  if (m) {
    const mes = MESES[m[1].toLowerCase()];
    if (mes !== undefined) return new Date(2000 + parseInt(m[2]), mes, 1);
  }
  return null;
}

/* Parsea un label de semana como "5 OCT", "28 DIC", "3 ENE" → Date (lunes de esa semana, año actual/siguiente) */
function _parseSemLabel(label) {
  const MESES = {ene:0,feb:1,mar:2,abr:3,may:4,jun:5,jul:6,ago:7,sep:8,oct:9,nov:10,dic:11};
  const m = label.match(/(\d{1,2})\s+([a-záéíóú]{2,3})/i);
  if (!m) return null;
  const mes = MESES[m[2].toLowerCase()];
  if (mes === undefined) return null;
  const hoyYear = new Date().getFullYear();
  // Si el mes ya pasó respecto a hoy, probablemente es el año siguiente
  const d1 = new Date(hoyYear, mes, parseInt(m[1]));
  const d2 = new Date(hoyYear + 1, mes, parseInt(m[1]));
  // Usar el año más cercano a la fecha actual que sea >= 3 meses antes de hoy
  const refDate = new Date(); refDate.setMonth(refDate.getMonth() - 3);
  return d1 >= refDate ? d1 : d2;
}

/* Genera labels de semanas adicionales a partir de la última semana conocida hasta targetDate */
function _extraWeekLabels(lastLabel, targetDate) {
  const MNAMES = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC'];
  let cur = _parseSemLabel(lastLabel);
  if (!cur) return [];
  const extra = [];
  cur = new Date(cur.getTime() + 7 * 24 * 3600 * 1000); // siguiente semana
  let safety = 0;
  while (cur <= targetDate && safety < 52) {
    extra.push(`${cur.getDate()} ${MNAMES[cur.getMonth()]}`);
    cur = new Date(cur.getTime() + 7 * 24 * 3600 * 1000);
    safety++;
  }
  return extra;
}

function ganttCompleto(proj) {
  const baseSems = PLANNING_DATA?.semanas || [];
  const hoy      = hoySemana();
  if (!baseSems.length) return '<p style="color:var(--ink3);font-size:12px;">Sin datos de planning.</p>';

  // Calcular horizonte: max(fin_obra, montaje) del proyecto
  const dFinObra  = _parseFechaProyecto(proj.fin_obra  || '');
  const dMontaje  = _parseFechaProyecto(proj.montaje   || '');
  let targetDate = null;
  if (dFinObra && dMontaje) targetDate = dFinObra > dMontaje ? dFinObra : dMontaje;
  else targetDate = dFinObra || dMontaje;

  // Último label del planning base
  const lastBaseSem = baseSems[baseSems.length - 1];
  const dLastBase   = _parseSemLabel(lastBaseSem);

  // Añadir semanas sintéticas si targetDate supera el último label base
  // Añadimos un margen de +6 días para incluir la semana que contiene targetDate
  let sems = [...baseSems];
  if (targetDate && dLastBase) {
    const targetPlusPadding = new Date(targetDate.getTime() + 6 * 24 * 3600 * 1000);
    if (targetPlusPadding > dLastBase) {
      const extra = _extraWeekLabels(lastBaseSem, targetPlusPadding);
      sems = [...sems, ...extra];
    }
  }

  const N    = sems.length;
  const colW = `repeat(${N},minmax(28px,1fr))`;
  const minW = `${N * 30}px`; // para forzar scroll horizontal

  let weeksHtml = `<div style="display:grid;grid-template-columns:${colW};gap:1px;margin-bottom:2px;min-width:${minW};">`;
  sems.forEach(sem => {
    const isHoy = sem === hoy;
    const isSynt = !baseSems.includes(sem); // semana sintética (fuera del planning)
    weeksHtml += `<div style="font-size:8.5px;font-weight:${isHoy?700:500};letter-spacing:.02em;
      text-align:center;padding:3px 1px;
      color:${isHoy?'var(--burg)':isSynt?'var(--ink3)':'var(--ink3)'};
      opacity:${isSynt?0.55:1};
      border-bottom:${isHoy?'2px solid var(--burg)':'1px solid transparent'};">${sem}</div>`;
  });
  weeksHtml += '</div>';

  // Determinar si el proyecto está oficialmente parado
  const estadoRaw = (proj.estado || proj._g?.fase_real || proj.fase || '').toUpperCase();
  const isParado  = /PARAD|ESPERA|STANDBY|STOP|HOLD/.test(estadoRaw);

  // Determinar rango activo del proyecto: primera y última semana con actividad registrada
  const timeline   = proj._p?.timeline || [];
  const activeSems = new Set(timeline.filter(t => t.actividades?.length).map(t => t.semana));
  let firstActive  = null, lastActive = null;
  sems.forEach(sem => {
    if (activeSems.has(sem)) {
      if (!firstActive) firstActive = sem;
      lastActive = sem;
    }
  });
  // Si no está parado, extender lastActive hasta hoy (la semana actual también es "activa")
  if (!isParado && lastActive) {
    const lastIdx_ = sems.indexOf(lastActive);
    const hoyIdx_  = sems.indexOf(hoy);
    if (hoyIdx_ >= 0 && hoyIdx_ > lastIdx_) lastActive = hoy;
  }
  const firstIdx = firstActive ? sems.indexOf(firstActive) : -1;
  const lastIdx  = lastActive  ? sems.indexOf(lastActive)  : -1;

  // Mapa semana→fase para forward-fill: celdas vacías heredan la última fase conocida
  const textoMapC = {};
  sems.forEach(sem => {
    const entry = timeline.find(t => t.semana === sem);
    textoMapC[sem] = entry?.actividades?.[0]?.texto || '';
  });

  let cellsHtml = `<div style="display:grid;grid-template-columns:${colW};gap:1px;min-width:${minW};">`;
  sems.forEach((sem, i) => {
    const registrado = textoMapC[sem] || '';
    const isSynt     = !baseSems.includes(sem);
    const inActiveRange = firstIdx >= 0 && lastIdx >= 0 && i >= firstIdx && i <= lastIdx;
    // Forward-fill: semana vacía en rango activo hereda última fase conocida
    let texto = registrado;
    let isFilled = false;
    if (!texto && !isParado && inActiveRange) {
      let fill = '';
      for (let k = firstIdx; k <= i; k++) {
        if (textoMapC[sems[k]]) fill = textoMapC[sems[k]];
      }
      if (fill) { texto = fill; isFilled = true; }
    }
    const ph           = texto ? faseColor(texto) : '';
    const isParadaCell = !registrado && isParado && inActiveRange;
    const clsParts     = ['gantt-cell'];
    if (ph)           clsParts.push(ph, 'filled');
    if (isFilled)     clsParts.push('ph-continuidad');
    if (isParadaCell) clsParts.push('ph9', 'filled');
    if (sem === hoy)  clsParts.push('gantt-cell-hoy');
    const cls     = clsParts.join(' ');
    const bgStyle = isSynt && !texto && !isParadaCell ? 'background:rgba(0,0,0,.02);' : '';
    const titleTxt = registrado    ? `: ${registrado}`
                   : isFilled      ? `: ${texto} (continuidad de fase)`
                   : isParadaCell  ? ' (proyecto parado)'
                   : '';
    const labelTxt = registrado || isFilled ? abrev(texto) : isParadaCell ? '···' : '';
    cellsHtml += `<div class="${cls}" title="${sem}${titleTxt}"
      style="height:30px;display:flex;align-items:center;justify-content:center;border-radius:3px;${bgStyle}">
      ${labelTxt ? `<span class="gantt-label" style="font-size:8.5px;font-weight:600;">${labelTxt}</span>` : ''}
    </div>`;
  });
  cellsHtml += '</div>';

  const note = targetDate && sems.length > baseSems.length
    ? `<div style="font-size:9px;color:var(--ink3);margin-top:6px;opacity:.7;">
        * Semanas extendidas hasta ${targetDate.toLocaleDateString('es-ES',{month:'short',year:'numeric'})}
        (${dFinObra&&dMontaje?'max(fin obra, montaje)':dFinObra?'fin de obra previsto':'montaje previsto'})
       </div>`
    : '';

  return `<div style="overflow-x:auto;padding-bottom:4px;">${weeksHtml}${cellsHtml}${note}</div>`;
}

function _planningLegend() {
  const items = [
    ['ph1','Proyecto/Diseño'],['ph2','Obra'],['ph3','Montaje'],['ph4','Entrega'],
    ['ph5','Renders'],['ph6','Visita'],['ph7','Pedidos/Remates'],['ph9','Parada'],
    ['ph-continuidad ph1','Continuidad de fase'],['ph-pending','Sin planificación definida'],
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
  const hasTimeline = (proj._p?.timeline?.length || 0) > 0;
  const ganttHtml = (opts.gantt !== false && hasTimeline) ? ganttGeneral(proj) : '';

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
      <div class="modal modal-ficha">

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

        <div class="modal-body" style="overflow-y:auto;flex:1;padding:0 24px 16px;display:grid;grid-template-columns:minmax(280px,2fr) minmax(320px,3fr);gap:0 24px;min-height:0;">

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
  'HOTELES':      ['Marta','Jesús','Jesus'],
  'RESTAURANTES': ['Sofía','Sofia','Naiara'],
  'VIVIENDA':     ['Olatz','Sara','Andrea','Paula','Cristina','Nela'],
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
  // Panel de Dirección: muestra EXCLUSIVAMENTE intervenciones escaladas por el PM.
  // No muestra información operativa del equipo (alertas, Gantt, cargas, objetivos completos).
  // Especificación v1.1 aprobada: secciones Decisiones urgentes, Próximas intervenciones,
  // Reuniones con su presencia, Resueltas recientemente.
  const sem = hoySemana();

  const int_d = (typeof INTERVENCIONES_DIR !== 'undefined') ? INTERVENCIONES_DIR : null;
  const intervenciones = (int_d && int_d.intervenciones) ? int_d.intervenciones : [];

  // Decisiones urgentes: Pendiente/En revisión con fecha_limite ≤ 5 días
  const urgentes = intervenciones.filter(i => {
    if (i.estado === 'Resuelta' || i.estado === 'Descartada') return false;
    const d = diasRestantes(i.fecha_limite);
    return d !== null && d <= 5;
  }).sort((a,b) => (a.fecha_limite||'').localeCompare(b.fecha_limite||''));

  // Próximas intervenciones: 6–14 días
  const proximas = intervenciones.filter(i => {
    if (i.estado === 'Resuelta' || i.estado === 'Descartada') return false;
    const d = diasRestantes(i.fecha_limite);
    return d !== null && d >= 6 && d <= 14;
  }).sort((a,b) => (a.fecha_limite||'').localeCompare(b.fecha_limite||''));

  // Reuniones con presencia de Alejandra
  const reuniones = intervenciones.filter(i =>
    i.tipo === 'Reunión' && i.estado !== 'Resuelta' && i.estado !== 'Descartada'
  ).sort((a,b) => (a.fecha_limite||'').localeCompare(b.fecha_limite||''));

  // Resueltas recientemente: últimas 7 con decision_adoptada (gravedad_pm nunca expuesto)
  const resueltas = intervenciones
    .filter(i => i.estado === 'Resuelta' && i.decision_adoptada)
    .sort((a,b) => (b.fecha_resolucion||'').localeCompare(a.fecha_resolucion||''))
    .slice(0, 7);

  const totalPendientes = urgentes.length + proximas.length;

  // Índice de navegación
  const indiceHtml = `
    <div class="idx-nav" style="margin-bottom:20px;">
      ${urgentes.length  ? indexBtn('ale-int-urgentes',  '● URGENTE',           BG_ALERTA,    BORDE_ALERTA,  urgentes.length)  : ''}
      ${proximas.length  ? indexBtn('ale-int-proximas',  'PRÓXIMAS',            BG_PROX,      BORDE_PROX,    proximas.length)  : ''}
      ${reuniones.length ? indexBtn('ale-int-reuniones', 'REUNIONES',           BG_SEMANA,    BORDE_SEMANA,  reuniones.length) : ''}
      ${resueltas.length ? indexBtn('ale-int-resueltas', 'RESUELTAS',           'var(--bg2)', '#2a7a2a',     resueltas.length) : ''}
    </div>`;

  let html = `<div class="view-head">
    <div>
      <div class="view-title">DIRECCIÓN</div>
      <div class="view-sub">${sem}${totalPendientes ? ` · ${totalPendientes} intervención${totalPendientes!==1?'es':''} pendiente${totalPendientes!==1?'s':''}` : ' · sin intervenciones pendientes'}</div>
    </div>
  </div>
  ${indiceHtml}`;

  // Helper fila de intervención para Alejandra (sin gravedad_pm)
  function intRowAle(i) {
    const tipoColor = {Decisión:'#c00',Aprobación:'#b06000',Reunión:'#005f9e',Negociación:'#600060',Supervisión:'#444'}[i.tipo]||'#444';
    const dias = diasRestantes(i.fecha_limite);
    const diasStr = dias === null ? '—'
      : dias < 0 ? `<span style="color:#c00;font-weight:600;">vencida +${Math.abs(dias)}d</span>`
      : dias === 0 ? `<span style="color:#c00;font-weight:600;">hoy</span>`
      : dias <= 2 ? `<span style="color:#c00;font-weight:600;">${dias}d</span>`
      : `${dias}d`;
    // Opciones si es Decisión o Aprobación
    const opcionesHtml = (i.opciones && i.opciones.length && (i.tipo === 'Decisión' || i.tipo === 'Aprobación'))
      ? `<div style="margin-top:4px;font-size:10.5px;color:var(--ink3);">${i.opciones.map(o=>`<span style="margin-right:10px;">▸ <strong>${o.label}</strong>: ${o.consecuencia}</span>`).join('')}</div>`
      : '';
    return `<tr style="border-top:1px solid var(--rule);">
      <td style="padding:6px 4px 6px 0;font-size:12px;font-weight:500;">${i.proyecto||'—'}<br>
        <span style="font-size:10px;color:var(--ink3);font-weight:400;">${i.departamento||''}</span></td>
      <td style="padding:6px 4px;vertical-align:top;"><span style="font-size:10px;font-weight:600;color:${tipoColor};">${i.tipo||'—'}</span></td>
      <td style="padding:6px 4px;font-size:11.5px;color:var(--ink2);vertical-align:top;">${i.accion_concreta||'—'}${opcionesHtml}</td>
      <td style="padding:6px 4px;font-size:11px;color:var(--ink2);vertical-align:top;">${i.impacto_si_no_actua||'—'}</td>
      <td style="padding:6px 0 6px 4px;font-size:11px;white-space:nowrap;vertical-align:top;">${fmtFecha(i.fecha_limite)}<br><span style="font-size:10px;">(${diasStr})</span></td>
    </tr>`;
  }

  const theadInt = `<thead><tr>
    <th style="width:18%;">Proyecto</th><th style="width:12%;">Tipo</th>
    <th style="width:32%;">Qué se necesita</th><th style="width:28%;">Impacto si no actúas</th>
    <th style="width:10%;">Límite</th>
  </tr></thead>`;

  if (urgentes.length) {
    html += `<div id="ale-int-urgentes" class="panel" style="background:${BG_ALERTA};border-left:3px solid #8b0000;">
      <div class="panel-head">
        <span class="eyebrow" style="color:#8b0000;">● DECISIONES URGENTES</span>
        <span style="font-size:11px;color:var(--ink3);font-weight:300;margin-left:6px;">límite ≤ 5 días · ${urgentes.length}</span>
      </div>
      <div class="tbl-wrap"><table class="tbl" style="width:100%;">${theadInt}
        <tbody>${urgentes.map(intRowAle).join('')}</tbody>
      </table></div>
    </div>`;
  }

  if (proximas.length) {
    html += `<div id="ale-int-proximas" class="panel" style="background:${BG_PROX};border-left:3px solid ${BORDE_PROX};">
      <div class="panel-head">
        <span class="eyebrow">PRÓXIMAS INTERVENCIONES</span>
        <span style="font-size:11px;color:var(--ink3);font-weight:300;margin-left:6px;">6–14 días · ${proximas.length}</span>
      </div>
      <div class="tbl-wrap"><table class="tbl" style="width:100%;">${theadInt}
        <tbody>${proximas.map(intRowAle).join('')}</tbody>
      </table></div>
    </div>`;
  }

  if (reuniones.length) {
    html += `<div id="ale-int-reuniones" class="panel" style="background:${BG_SEMANA};border-left:3px solid ${BORDE_SEMANA};">
      <div class="panel-head">
        <span class="eyebrow">REUNIONES CON TU PRESENCIA</span>
        <span style="font-size:11px;color:var(--ink3);font-weight:300;margin-left:6px;">${reuniones.length}</span>
      </div>
      <div class="tbl-wrap"><table class="tbl" style="width:100%;">
        <thead><tr><th>Proyecto</th><th>Acción</th><th>Impacto</th><th>Fecha</th></tr></thead>
        <tbody>${reuniones.map(intRowAle).join('')}</tbody>
      </table></div>
    </div>`;
  }

  if (resueltas.length) {
    const filasResueltas = resueltas.map(i =>
      `<tr style="border-top:1px solid var(--rule);">
        <td style="padding:5px 4px 5px 0;font-size:12px;">${i.proyecto||'—'}</td>
        <td style="padding:5px 4px;font-size:10px;font-weight:600;color:#2a7a2a;">Resuelta</td>
        <td style="padding:5px 4px;font-size:11px;color:var(--ink2);">${i.decision_adoptada||'—'}</td>
        <td style="padding:5px 4px;font-size:11px;color:var(--ink2);">${i.responsable_ejecucion||'—'}</td>
        <td style="padding:5px 0 5px 4px;font-size:11px;color:var(--ink3);">${fmtFecha(i.fecha_resolucion)}</td>
      </tr>`
    ).join('');
    html += `<div id="ale-int-resueltas" class="panel" style="background:var(--bg2);border-left:3px solid #2a7a2a;">
      <div class="panel-head"><span class="eyebrow" style="color:#2a7a2a;">RESUELTAS RECIENTEMENTE</span></div>
      <div class="tbl-wrap"><table class="tbl" style="width:100%;">
        <thead><tr><th>Proyecto</th><th>Estado</th><th>Decisión adoptada</th><th>Ejecuta</th><th>Fecha</th></tr></thead>
        <tbody>${filasResueltas}</tbody>
      </table></div>
    </div>`;
  }

  // Estado vacío: sin intervenciones publicadas
  if (!urgentes.length && !proximas.length && !reuniones.length && !resueltas.length) {
    html += `<div class="panel" style="background:var(--bg2);border-left:3px solid var(--rule);">
      <p class="panel-note" style="padding:16px 0;">Sin intervenciones publicadas esta semana.</p>
    </div>`;
  }

  document.getElementById('view').innerHTML = html;
}

/* ── Helpers — ciclo semanal ─────────────────────────────── */
function diasRestantes(fechaLimite) {
  if (!fechaLimite) return null;
  const hoy = new Date(); hoy.setHours(0,0,0,0);
  const lim = new Date(fechaLimite); lim.setHours(0,0,0,0);
  return Math.round((lim - hoy) / 86400000);
}

function fmtFecha(iso) {
  if (!iso) return '—';
  const [y,m,d] = iso.split('-');
  const meses = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
  return `${parseInt(d)} ${meses[parseInt(m)-1]}`;
}

function prioTag(p) {
  if (p === 'Alta')   return `<span style="color:#c00;font-size:10px;font-weight:600;text-transform:uppercase;">Alta</span>`;
  if (p === 'Media')  return `<span style="color:#b06000;font-size:10px;font-weight:600;text-transform:uppercase;">Media</span>`;
  return `<span style="color:var(--ink3);font-size:10px;">Baja</span>`;
}

function estadoObjTag(e) {
  const m = {Pendiente:'#666',Completado:'#2a7a2a',Bloqueado:'#c00',Arrastrado:'#b06000','En curso':'#005f9e'};
  return `<span style="color:${m[e]||'#666'};font-size:10px;font-weight:600;">${e||'—'}</span>`;
}

/* Render secciones ciclo semanal PM */
function renderCicloSemanalJavi() {
  const obj   = (typeof OBJETIVOS_SEMANA !== 'undefined') ? OBJETIVOS_SEMANA : null;
  const int_d = (typeof INTERVENCIONES_DIR !== 'undefined') ? INTERVENCIONES_DIR : null;
  const hoy   = new Date(); hoy.setHours(0,0,0,0);

  let html = '';

  /* ── 1. ESTA SEMANA — objetivos publicados ─────────────────── */
  const objetivos = (obj && obj.objetivos) ? obj.objetivos : [];
  if (objetivos.length) {
    // Agrupar por departamento
    const porDpto = {};
    objetivos.forEach(o => {
      const d = o.departamento || 'General';
      if (!porDpto[d]) porDpto[d] = [];
      porDpto[d].push(o);
    });
    // Ordenar cada grupo: Alta primero, luego por fecha_limite
    Object.values(porDpto).forEach(arr => arr.sort((a,b) => {
      const pp = {Alta:0,Media:1,Baja:2};
      if ((pp[a.prioridad]||1) !== (pp[b.prioridad]||1)) return (pp[a.prioridad]||1)-(pp[b.prioridad]||1);
      return (a.fecha_limite||'').localeCompare(b.fecha_limite||'');
    }));

    let filas = '';
    const deptos = ['Vivienda','Restaurantes','Hoteles','General'];
    deptos.forEach(d => {
      if (!porDpto[d]) return;
      filas += `<tr><td colspan="5" style="padding:6px 0 2px;font-size:10px;font-weight:600;color:var(--ink3);text-transform:uppercase;letter-spacing:.05em;">${d}</td></tr>`;
      porDpto[d].forEach(o => {
        const dias = diasRestantes(o.fecha_limite);
        const diasStr = dias === null ? '—' : dias < 0 ? `<span style="color:#c00">+${Math.abs(dias)}d</span>` : dias <= 2 ? `<span style="color:#c00">${dias}d</span>` : `${dias}d`;
        const arrastradoBadge = o.semanas_arrastrado > 0
          ? `<span style="color:#b06000;font-size:9px;margin-left:4px;">↩ ×${o.semanas_arrastrado}</span>` : '';
        filas += `<tr style="border-top:1px solid var(--rule);">
          <td style="padding:5px 4px 5px 0;font-size:12px;">${o.proyecto||'—'}${arrastradoBadge}</td>
          <td style="padding:5px 4px;font-size:11.5px;color:var(--ink2);">${o.responsable||'—'}</td>
          <td style="padding:5px 4px;">${prioTag(o.prioridad)}</td>
          <td style="padding:5px 4px;font-size:11px;color:var(--ink2);">${fmtFecha(o.fecha_limite)}&nbsp;(${diasStr})</td>
          <td style="padding:5px 0 5px 4px;">${estadoObjTag(o.estado)}</td>
        </tr>
        <tr><td colspan="5" style="padding:0 0 6px;font-size:11px;color:var(--ink2);">${o.descripcion||''}</td></tr>`;
      });
    });

    html += `<div id="pm-esta-semana" class="panel" style="background:${BG_SEMANA};border-left:3px solid ${BORDE_SEMANA};">
      <div class="panel-head"><span class="eyebrow">ESTA SEMANA</span>
        <span style="font-size:11px;color:var(--ink3);font-weight:300;margin-left:6px;">${obj.semana||''} · ${objetivos.length} objetivo${objetivos.length!==1?'s':''}</span>
      </div>
      <div class="tbl-wrap"><table class="tbl" style="width:100%;">
        <thead><tr>
          <th style="width:28%;">Proyecto</th><th style="width:14%;">Resp.</th>
          <th style="width:10%;">Prio</th><th style="width:18%;">Límite</th><th style="width:14%;">Estado</th>
        </tr></thead>
        <tbody>${filas}</tbody>
      </table></div>
    </div>`;
  }

  /* ── 2. INTERVENCIONES PENDIENTES DIRECCIÓN ────────────────── */
  const intervenciones = (int_d && int_d.intervenciones) ? int_d.intervenciones : [];
  const pendientes = intervenciones.filter(i => i.estado === 'Pendiente' || i.estado === 'En revisión');
  if (pendientes.length) {
    const filas = pendientes.map(i => {
      const dias = diasRestantes(i.fecha_limite);
      const diasStr = dias === null ? '—' : dias < 0 ? `<span style="color:#c00;font-weight:600;">VENCIDA +${Math.abs(dias)}d</span>` : dias <= 2 ? `<span style="color:#c00;font-weight:600;">${dias}d</span>` : `${dias}d`;
      const tipoColor = {Decisión:'#c00',Aprobación:'#b06000',Reunión:'#005f9e',Negociación:'#600060',Supervisión:'#444'}[i.tipo]||'#444';
      return `<tr style="border-top:1px solid var(--rule);">
        <td style="padding:5px 4px 5px 0;font-size:12px;">${i.proyecto||'—'}</td>
        <td style="padding:5px 4px;"><span style="font-size:10px;font-weight:600;color:${tipoColor};">${i.tipo||'—'}</span></td>
        <td style="padding:5px 4px;font-size:11px;color:var(--ink2);">${i.accion_concreta||'—'}</td>
        <td style="padding:5px 0 5px 4px;font-size:11px;">${fmtFecha(i.fecha_limite)}&nbsp;(${diasStr})</td>
      </tr>`;
    }).join('');

    html += `<div id="pm-intervenciones" class="panel" style="background:var(--bg2);border-left:3px solid #8b0000;">
      <div class="panel-head"><span class="eyebrow" style="color:#8b0000;">INTERVENCIONES · DIRECCIÓN</span>
        <span style="font-size:11px;color:var(--ink3);font-weight:300;margin-left:6px;">${pendientes.length} pendiente${pendientes.length!==1?'s':''}</span>
      </div>
      <div class="tbl-wrap"><table class="tbl" style="width:100%;">
        <thead><tr>
          <th style="width:22%;">Proyecto</th><th style="width:14%;">Tipo</th>
          <th style="width:44%;">Acción requerida</th><th style="width:20%;">Límite</th>
        </tr></thead>
        <tbody>${filas}</tbody>
      </table></div>
    </div>`;
  }

  /* ── 3. INTERVENCIONES RESUELTAS — REVISAR OBJETIVO ───────── */
  const objIds = new Set(objetivos.map(o => o.id));
  // También incluir bloqueados del historial reciente
  const todosBloqueados = new Set();
  (obj && obj.objetivos ? obj.objetivos : []).forEach(o => {
    if (o.estado === 'Bloqueado') todosBloqueados.add(o.id);
  });
  (obj && obj.historial ? obj.historial : []).forEach(sem => {
    (sem.objetivos||[]).forEach(o => { if (o.estado_final === 'Bloqueado') todosBloqueados.add(o.id); });
  });

  const resueltasRevisar = intervenciones.filter(i =>
    i.estado === 'Resuelta' && i.objetivo_vinculado_id && todosBloqueados.has(i.objetivo_vinculado_id)
  );
  if (resueltasRevisar.length) {
    const filas = resueltasRevisar.map(i =>
      `<tr style="border-top:1px solid var(--rule);">
        <td style="padding:5px 4px 5px 0;font-size:12px;">${i.proyecto||'—'}</td>
        <td style="padding:5px 4px;font-size:11px;color:#2a7a2a;font-weight:600;">Resuelta</td>
        <td style="padding:5px 4px;font-size:11px;color:var(--ink2);">${i.decision_adoptada||'—'}</td>
        <td style="padding:5px 0 5px 4px;font-size:11px;color:#c00;">Obj. ${i.objetivo_vinculado_id} — Bloqueado</td>
      </tr>`
    ).join('');
    html += `<div id="pm-revisar" class="panel" style="background:var(--bg2);border-left:3px solid #b06000;">
      <div class="panel-head"><span class="eyebrow" style="color:#b06000;">INTERVENCIÓN RESUELTA — REVISAR OBJETIVO</span></div>
      <div class="tbl-wrap"><table class="tbl" style="width:100%;">
        <thead><tr><th>Proyecto</th><th>Estado int.</th><th>Decisión adoptada</th><th>Objetivo</th></tr></thead>
        <tbody>${filas}</tbody>
      </table></div>
    </div>`;
  }

  /* ── 4. BLOQUEADOS SIN INTERVENCIÓN ───────────────────────── */
  // Objetivos en estado Bloqueado que NO tienen ninguna intervención vinculada activa
  const intIdsBloqueados = new Set(
    intervenciones
      .filter(i => i.estado !== 'Resuelta' && i.estado !== 'Descartada' && i.objetivo_vinculado_id)
      .map(i => i.objetivo_vinculado_id)
  );
  const bloqueadosSinInt = objetivos.filter(o =>
    o.estado === 'Bloqueado' && !intIdsBloqueados.has(o.id)
  );
  if (bloqueadosSinInt.length) {
    const filas = bloqueadosSinInt.map(o => {
      const dias = diasRestantes(o.fecha_limite);
      const diasStr = dias === null ? '—' : dias < 0 ? `<span style="color:#c00;font-weight:600;">+${Math.abs(dias)}d</span>` : dias <= 2 ? `<span style="color:#c00;font-weight:600;">${dias}d</span>` : `${dias}d`;
      return `<tr style="border-top:1px solid var(--rule);">
        <td style="padding:5px 4px 5px 0;font-size:12px;font-weight:500;">${o.proyecto||'—'}</td>
        <td style="padding:5px 4px;font-size:11px;color:var(--ink2);">${o.responsable||'—'}</td>
        <td style="padding:5px 4px;">${prioTag(o.prioridad)}</td>
        <td style="padding:5px 4px;font-size:11px;color:var(--ink2);">${fmtFecha(o.fecha_limite)}&nbsp;(${diasStr})</td>
        <td style="padding:5px 4px;font-size:11px;color:var(--ink2);max-width:200px;">${o.descripcion||'—'}</td>
      </tr>`;
    }).join('');
    html += `<div id="pm-bloqueados" class="panel" style="background:${BG_ALERTA};border-left:3px solid #8b0000;">
      <div class="panel-head">
        <span class="eyebrow" style="color:#8b0000;">● BLOQUEADOS SIN INTERVENCIÓN</span>
        <span style="font-size:11px;color:var(--ink3);font-weight:300;margin-left:6px;">${bloqueadosSinInt.length} objetivo${bloqueadosSinInt.length!==1?'s':''} · escalar a Dirección</span>
      </div>
      <div class="tbl-wrap"><table class="tbl" style="width:100%;">
        <thead><tr>
          <th style="width:22%;">Proyecto</th><th style="width:14%;">Responsable</th>
          <th style="width:10%;">Prio</th><th style="width:16%;">Límite</th><th style="width:38%;">Objetivo</th>
        </tr></thead>
        <tbody>${filas}</tbody>
      </table></div>
    </div>`;
  }

  /* ── 5. ARRASTRADOS EN REVISIÓN (> 2 semanas) ──────────────── */
  const arrastrados = objetivos.filter(o => (o.semanas_arrastrado||0) > 2);
  if (arrastrados.length) {
    const filas = arrastrados.map(o =>
      `<tr style="border-top:1px solid var(--rule);">
        <td style="padding:5px 4px 5px 0;font-size:12px;">${o.proyecto||'—'}</td>
        <td style="padding:5px 4px;font-size:11px;color:var(--ink2);">${o.responsable||'—'}</td>
        <td style="padding:5px 4px;font-size:11px;color:#b06000;font-weight:600;">${o.semanas_arrastrado} semanas</td>
        <td style="padding:5px 0 5px 4px;font-size:11px;color:var(--ink2);">${o.descripcion||'—'}</td>
      </tr>`
    ).join('');
    html += `<div id="pm-arrastrados" class="panel" style="background:var(--bg2);border-left:3px solid #b06000;">
      <div class="panel-head"><span class="eyebrow" style="color:#b06000;">ARRASTRADOS EN REVISIÓN</span>
        <span style="font-size:11px;color:var(--ink3);font-weight:300;margin-left:6px;">${arrastrados.length} objetivo${arrastrados.length!==1?'s':''} · más de 2 semanas</span>
      </div>
      <div class="tbl-wrap"><table class="tbl" style="width:100%;">
        <thead><tr><th>Proyecto</th><th>Responsable</th><th>Arrastrado</th><th>Objetivo</th></tr></thead>
        <tbody>${filas}</tbody>
      </table></div>
    </div>`;
  }

  return html;
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

  /* Secciones del ciclo semanal — antes de los grupos de estado */
  html += renderCicloSemanalJavi();

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
      ${prioridad.map(p => projCard(p, {gantt:true})).join('')}
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
      ${otrosProyectos.map(p => projCard(p, {gantt:true})).join('')}
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
