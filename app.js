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

/* ── Carga persona ───────────────────────────────────────── */
function cargaPersona(nombre) {
  const hoy = hoySemana();
  return (MASTER_DATA||[]).filter(p =>
    (p.equipo||[]).includes(nombre) &&
    (planOf(p.id)?.timeline||[]).some(t => t.semana === hoy)
  ).length;
}

/* ── Personas dinámicas ──────────────────────────────────── */
function getPersonas() {
  const s = new Set();
  (MASTER_DATA||[]).forEach(p => (p.equipo||[]).forEach(n => { if(n) s.add(n); }));
  return [...s].sort();
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

/* ── Gantt general (ventana 12 sem) ─────────────────────── */
function ganttGeneral(proj) {
  const ventana = semanaWindow();
  const plan    = proj._p;
  const hoy     = hoySemana();
  if (!ventana.length) return '';

  // Meses para cabecera agrupada
  let mesActual = '', mesHtml = '<div class="gantt-months">';
  ventana.forEach(sem => {
    const partes = sem.split('/'); // W41/2026
    // Aproximar mes por número de semana
    mesHtml += `<div class="gantt-month"></div>`;
  });
  mesHtml += '</div>';

  let cellsHtml = '<div class="gantt-grid">';
  ventana.forEach(sem => {
    const esHoy  = sem === hoy;
    const entry  = plan?.timeline.find(t => t.semana === sem);
    const act    = entry?.actividades?.[0];
    const texto  = act?.texto || '';
    // Fase → color de celda
    let phCls = texto ? faseColor(texto) : '';
    let cls = `gantt-cell${phCls ? ' '+phCls+' filled' : ''}`;
    const title = `${sem}${texto ? ': '+texto : ''}`;
    cellsHtml += `<div class="${cls}" title="${title}" data-sem="${sem}" data-id="${proj.id}">
      ${texto ? `<span class="gantt-label">${abrev(texto)}</span>` : ''}
    </div>`;
  });
  cellsHtml += '</div>';

  // Marcador de hoy
  const hoyIdx = ventana.indexOf(hoy);
  let todayHtml = '';
  if (hoyIdx >= 0) {
    const pct = (hoyIdx / ventana.length * 100).toFixed(1);
    todayHtml = `<div class="gantt-row" style="position:relative;">
      <div class="gantt-today" style="left:calc(${pct}% + ${hoyIdx}px)"></div>
      <div class="gantt-today-lbl" style="left:calc(${pct}% + ${hoyIdx+4}px)">HOY</div>
    </div>`;
  }

  return `<div class="gantt">${mesHtml}<div class="gantt-row" style="position:relative;">${todayHtml}${cellsHtml}</div></div>`;
}

/* ── Gantt completo (modal) ─────────────────────────────── */
function ganttCompleto(proj) {
  const sems = PLANNING_DATA?.semanas || [];
  const plan  = proj._p;
  const hoy   = hoySemana();
  if (!sems.length) return '<p style="color:var(--ink3);font-size:12px;">Sin datos de planning.</p>';

  let cellsHtml = '<div class="gantt-grid" style="grid-template-columns:repeat('+sems.length+',1fr)">';
  sems.forEach(sem => {
    const esHoy = sem === hoy;
    const entry = plan?.timeline.find(t => t.semana === sem);
    const texto = entry?.actividades?.[0]?.texto || '';
    let phCls = texto ? faseColor(texto) : '';
    let cls = `gantt-cell${phCls?' '+phCls+' filled':''}${esHoy?' gantt-cell-hoy':''}`;
    cellsHtml += `<div class="${cls}" title="${sem}${texto?': '+texto:''}">${texto?`<span class="gantt-label">${abrev(texto)}</span>`:''}</div>`;
  });
  cellsHtml += '</div>';

  let weeksHtml = '<div class="gantt-weeks" style="grid-template-columns:repeat('+sems.length+',1fr)">';
  sems.forEach(sem => {
    weeksHtml += `<div class="gantt-week${sem===hoy?' gantt-week-hoy':''}">${sem.split('/')[0]}</div>`;
  });
  weeksHtml += '</div>';

  return `<div class="gantt">${cellsHtml}${weeksHtml}</div>`;
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
  if (t.includes('OBRA'))   return 'ph2';
  if (t.includes('MONTAJ')) return 'ph3';
  if (t.includes('ENTREGA'))return 'ph4';
  if (t.includes('RENDER')) return 'ph5';
  if (t.includes('VISITA')) return 'ph6';
  if (t.includes('PEDIDO')) return 'ph7';
  if (t.includes('PARAD') || t.includes('ESPERA')) return 'ph9';
  return 'ph1';
}

/* ── Tarjeta de proyecto ─────────────────────────────────── */
function projCard(proj, opts={}) {
  const g    = proj._g;
  const done = S.get(proj.id,'done')==='1';
  const [dCls, dTxt] = deptTag(proj.dpto);
  const [rCls, rTxt] = riskTag(g?.atencion);
  const hito    = g?.proximo_hito || '';
  const fecha   = g?.fecha_hito   || '';
  const bloq    = g?.bloqueador   || '';
  const equipo  = (proj.equipo||[]).map(e=>`<span style="font-size:11px;color:var(--ink3)">${e}</span>`).join(' · ');
  const note    = S.get(proj.id,'note');

  const hitoHtml = hito
    ? `<div class="hito-row"><span class="hito-text">${hito}</span>${fecha?`<span class="hito-date">${fecha}</span>`:''}</div>`
    : '';
  const bloqHtml = bloq
    ? `<div style="font-size:11.5px;color:var(--crit);margin:4px 0;">⚠ ${bloq}</div>`
    : '';
  const ganttHtml = opts.gantt !== false ? ganttGeneral(proj) : '';
  const equipoHtml = equipo ? `<div style="margin-top:6px;">${equipo}</div>` : '';

  return `<div class="proj-card${done?' proj-done':''}" data-id="${proj.id}">
    <div class="proj-top">
      <div>
        <div class="proj-tags" style="margin-bottom:5px;">
          ${tagHtml(dCls,dTxt)} ${tagHtml(rCls,rTxt)}
          ${proj.fase?`<span class="tag tag-out">${proj.fase}</span>`:''}
        </div>
        <div class="proj-name" style="cursor:pointer;" data-open="${proj.id}">${proj.nombre}</div>
      </div>
      <div style="display:flex;gap:6px;align-items:flex-start;flex-shrink:0;">
        <button class="btn-done btn-ghost" data-done="${proj.id}" style="font-size:16px;padding:2px 8px;line-height:1;">${done?'✓':'○'}</button>
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
  const raw = MASTER_DATA.find(p => p.id === id);
  if (!raw) return;
  _modalId = id;
  const proj = enrich(raw);
  const g    = proj._g;
  const plan = proj._p;

  const equipoHtml = (proj.equipo||[]).map(e =>
    `<span class="tag tag-out">${e} <small style="color:var(--cop)">${cargaPersona(e)} proy</small></span>`
  ).join(' ');

  const planHtml = (plan?.timeline||[]).length
    ? `<div style="display:flex;flex-direction:column;gap:4px;">
        ${plan.timeline.map(t => `
          <div style="display:flex;gap:8px;align-items:baseline;">
            <span style="font-size:10px;font-weight:600;letter-spacing:.06em;color:${t.semana===hoySemana()?'var(--burg)':'var(--cop)'};">${t.semana}</span>
            ${t.actividades.map(a=>`<span style="font-size:12.5px;color:var(--ink2);">${a.texto}</span>`).join(', ')}
          </div>`).join('')}
      </div>`
    : '<p style="font-size:12px;color:var(--ink3);">Sin actividad registrada en planning.</p>';

  const decoHtml = (proj.deco_cerrada||proj.presupuesto_deco_aceptado||proj.pedidos_confirmados)
    ? `<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:4px;">
        <span class="tag ${proj.deco_cerrada==='SÍ'?'tag-baj':'tag-out'}">Deco cerrada: ${proj.deco_cerrada||'—'}</span>
        <span class="tag ${proj.presupuesto_deco_aceptado==='SÍ'?'tag-baj':'tag-out'}">Ppto aceptado: ${proj.presupuesto_deco_aceptado||'—'}</span>
        <span class="tag ${proj.pedidos_confirmados==='SÍ'?'tag-baj':'tag-out'}">Pedidos: ${proj.pedidos_confirmados||'—'}</span>
      </div>` : '';

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
          <div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:10px;">
            ${tagHtml(...deptTag(proj.dpto))} ${tagHtml(...riskTag(g?.atencion))}
          </div>
          ${g?.bloqueador?`<div style="color:var(--crit);font-size:12.5px;margin-bottom:10px;">⚠ ${g.bloqueador}</div>`:''}
          <table style="width:100%;font-size:12.5px;border-collapse:collapse;margin-bottom:12px;">
            ${row2('Próximo hito', g?.proximo_hito||'—')}
            ${row2('Fecha hito', g?.fecha_hito||'—')}
            ${row2('Constructora', proj.constructora||'—')}
            ${row2('Fin obra', proj.fin_obra||'—')}
            ${row2('Montaje', proj.montaje||'—')}
            ${row2('Fin oficial', proj.fin_oficial||'—')}
            ${row2('Estado', proj.estado||'—')}
          </table>
          ${decoHtml}
          ${equipoHtml?`<div style="margin:10px 0;">${equipoHtml}</div>`:''}
          ${proj.obs?`<p style="font-size:12px;color:var(--ink2);margin-bottom:10px;">${proj.obs}</p>`:''}
          <div style="margin-top:14px;">
            <div class="eyebrow" style="margin-bottom:8px;">Planning completo</div>
            ${ganttCompleto(proj)}
            <div style="margin-top:8px;">${planHtml}</div>
          </div>
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

  // Eliminar modal anterior si existe
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
}

function row2(k, v) {
  return `<tr><td style="color:var(--ink3);font-size:10px;letter-spacing:.08em;text-transform:uppercase;padding:4px 0;width:110px;">${k}</td><td style="padding:4px 0;">${v}</td></tr>`;
}

function closeModal() {
  const note = document.getElementById('modal-note');
  if (note && _modalId) S.set(_modalId, 'note', note.value);
  document.getElementById('modal-bg')?.remove();
  _modalId = null;
}

/* ── Render Javi / PM ────────────────────────────────────── */
function renderJavi() {
  const dptos = ['vivienda','restaurantes','hoteles'];
  const bloqueados = (MASTER_DATA||[]).filter(p => globalOf(p.id)?.bloqueador);

  let html = `<div class="view-head">
    <div>
      <div class="view-title">Javi · Master</div>
      <div class="view-sub">Semana ${hoySemana()}</div>
    </div>
    <div class="view-tags">
      ${tagHtml('tag-viv','● Vivienda')}
      ${tagHtml('tag-hot','● Hoteles')}
      ${tagHtml('tag-rest','● Restaurantes')}
    </div>
  </div>`;

  if (bloqueados.length) {
    html += `<div class="panel">
      <div class="panel-head"><span class="eyebrow">Bloqueadores activos · ${bloqueados.length}</span></div>
      <div>
        ${bloqueados.map(p => {
          const g = globalOf(p.id);
          return `<div class="sem-card crit" style="cursor:pointer;" data-open="${p.id}">
            <div class="sem-week">${p.nombre} <span style="font-weight:300;font-size:10px;">${p.dpto}</span></div>
            <div class="sem-items">⚠ ${g?.bloqueador}</div>
          </div>`;
        }).join('')}
      </div>
    </div>`;
  }

  dptos.forEach(dpto => {
    const proyectos = (MASTER_DATA||[]).filter(p => p.dpto === dpto).map(enrich);
    if (!proyectos.length) return;
    const label = dpto === 'vivienda' ? 'Vivienda' : dpto === 'restaurantes' ? 'Restaurantes' : 'Hoteles';
    const tagCls = dpto === 'vivienda' ? 'tag-viv' : dpto === 'restaurantes' ? 'tag-rest' : 'tag-hot';
    html += `<div class="panel">
      <div class="panel-head">
        <span class="eyebrow">${label} · ${proyectos.length}</span>
      </div>
      ${proyectos.map(p => projCard(p)).join('')}
    </div>`;
  });

  document.getElementById('view').innerHTML = html;
}

/* ── Render Alejandra / CEO ──────────────────────────────── */
function renderAlejandra() {
  const prioritarios = (MASTER_DATA||[]).map(enrich).filter(p => {
    const a = (p._g?.atencion||'').toUpperCase();
    return a.includes('MÁXIMA')||a.includes('MAXIMA')||a.includes('ALTA');
  });

  const proximos = (MASTER_DATA||[]).map(enrich)
    .filter(p => p._g?.fecha_hito)
    .sort((a,b) => (a._g.fecha_hito < b._g.fecha_hito ? -1 : 1))
    .slice(0, 10);

  let html = `<div class="view-head">
    <div>
      <div class="view-title">Alejandra · CEO</div>
      <div class="view-sub">Semana ${hoySemana()} · ${prioritarios.length} proyectos requieren atención</div>
    </div>
  </div>`;

  html += `<div class="panel">
    <div class="panel-head"><span class="eyebrow">Atención requerida · ${prioritarios.length}</span></div>
    ${prioritarios.length
      ? prioritarios.map(p => projCard(p, {gantt:false})).join('')
      : '<p class="panel-note">Sin proyectos en atención alta.</p>'}
  </div>`;

  if (proximos.length) {
    html += `<div class="panel">
      <div class="panel-head"><span class="eyebrow">Próximos hitos</span></div>
      <div class="tbl-wrap"><table class="tbl">
        <thead><tr>
          <th>Proyecto</th><th>Dpto</th><th>Hito</th><th>Fecha</th>
        </tr></thead>
        <tbody>
          ${proximos.map(p => `<tr style="cursor:pointer;" data-open="${p.id}">
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
  const todos    = (MASTER_DATA||[]).filter(p => (p.equipo||[]).includes(nombre)).map(enrich);
  const hoy      = hoySemana();
  const activos  = todos.filter(p => (p._p?.timeline||[]).some(t => t.semana === hoy));
  const resto    = todos.filter(p => !activos.includes(p));
  const carga    = activos.length;

  let html = `<div class="view-head">
    <div>
      <div class="view-title">${nombre}</div>
      <div class="view-sub">${todos.length} proyectos · ${carga} activos esta semana (${hoy})</div>
    </div>
  </div>`;

  if (activos.length) {
    html += `<div class="panel">
      <div class="panel-head"><span class="eyebrow">Esta semana · ${hoy}</span></div>
      ${activos.map(p => projCard(p)).join('')}
    </div>`;
  }

  if (resto.length) {
    html += `<div class="panel">
      <div class="panel-head"><span class="eyebrow">Resto de proyectos · ${resto.length}</span></div>
      ${resto.map(p => projCard(p, {gantt:false})).join('')}
    </div>`;
  }

  if (!todos.length) {
    html += '<p class="panel-note" style="margin-top:20px;">Sin proyectos asignados.</p>';
  }

  document.getElementById('view').innerHTML = html;
}

/* ── Tabs ─────────────────────────────────────────────────── */
let curTab = 'javi';

function buildTabs() {
  const personas = getPersonas();
  const tabsEl   = document.getElementById('tabs');
  if (!tabsEl) return;

  const fixed = [
    { id:'javi',      label:'Javi · Master', cls:'tab-master' },
    { id:'alejandra', label:'Alejandra · CEO' },
  ];
  const pTabs = personas.map(n => ({
    id: 'p__' + n.toLowerCase().replace(/\s+/g,'_'),
    label: n,
    nombre: n
  }));

  tabsEl.innerHTML = [...fixed, ...pTabs].map(t =>
    `<button class="tab ${t.cls||''} ${t.id===curTab?'active':''}" data-tab="${t.id}">${t.label}</button>`
  ).join('');
}

function activateTab(id) {
  curTab = id;
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('active', b.dataset.tab === id));

  if (id === 'javi')      renderJavi();
  else if (id === 'alejandra') renderAlejandra();
  else if (id.startsWith('p__')) {
    const slug = id.slice(3);
    const nombre = getPersonas().find(n => n.toLowerCase().replace(/\s+/g,'_') === slug);
    if (nombre) renderPersona(nombre);
  }
}

/* ── Exportar ─────────────────────────────────────────────── */
function exportar() {
  const hoy = new Date().toLocaleDateString('es-ES');
  const sem = hoySemana();
  const lines = [`POMBO ESTUDIO — ${hoy} (${sem})`, '='.repeat(50), ''];

  ['vivienda','restaurantes','hoteles'].forEach(dpto => {
    const ps = (MASTER_DATA||[]).filter(p => p.dpto === dpto);
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
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
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
      const id = done.dataset.done;
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
  document.addEventListener('keydown', e => { if (e.key==='Escape') closeModal(); });
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
