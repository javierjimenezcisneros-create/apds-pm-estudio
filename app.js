/* ============================================================
   POMBO ESTUDIO — app.js
   Trabaja exclusivamente con MASTER_DATA, GLOBAL_DATA, PLANNING_DATA, META
   Todos los datos inyectados por generate_app.py
   ============================================================ */

/* ──────────────────────────────────────────────
   ESTADO LOCAL (localStorage)
   Checkboxes y notas por persona/proyecto
   ────────────────────────────────────────────── */
const S = {
  key: (pid, field) => `pombo_${pid}_${field}`,
  get: (pid, field, def = '') => {
    try { return localStorage.getItem(S.key(pid, field)) ?? def; }
    catch { return def; }
  },
  set: (pid, field, val) => {
    try { localStorage.setItem(S.key(pid, field), val); }
    catch {}
  },
  toggle: (pid, field) => {
    const v = S.get(pid, field, '0') === '1' ? '0' : '1';
    S.set(pid, field, v);
    return v === '1';
  }
};

/* ──────────────────────────────────────────────
   CRUCE DE DATOS: indexar GLOBAL y PLANNING por id
   ────────────────────────────────────────────── */
let _globalIdx = null;
let _planIdx   = null;

function buildIndexes() {
  _globalIdx = {};
  (GLOBAL_DATA || []).forEach(g => { _globalIdx[g.id] = g; });

  _planIdx = {};
  ((PLANNING_DATA || {}).proyectos || []).forEach(p => { _planIdx[p.id] = p; });
}

function globalOf(id) { return _globalIdx?.[id] || null; }
function planOf(id)   { return _planIdx?.[id]   || null; }

/* Enriquece un proyecto MASTER con datos de GLOBAL y PLANNING */
function enrich(proj) {
  return {
    ...proj,
    _global:   globalOf(proj.id),
    _plan:     planOf(proj.id),
  };
}

/* ──────────────────────────────────────────────
   SEMANA ACTUAL
   ────────────────────────────────────────────── */
function hoySemana() {
  return META?.hoy_semana || '';
}

/* Índice de una semana en PLANNING_DATA.semanas */
function semanaIdx(semana) {
  return (PLANNING_DATA?.semanas || []).indexOf(semana);
}

/* ──────────────────────────────────────────────
   CARGA POR PERSONA (calculada en APP)
   Cuenta proyectos activos de una persona en la semana actual
   ────────────────────────────────────────────── */
function cargaPersona(nombre) {
  const hoy = hoySemana();
  return (MASTER_DATA || []).filter(p => {
    if (!(p.equipo || []).includes(nombre)) return false;
    const plan = planOf(p.id);
    if (!plan) return false;
    return plan.timeline.some(t => t.semana === hoy);
  }).length;
}

/* ──────────────────────────────────────────────
   PERSONAS DEL EQUIPO (derivadas dinámicamente)
   ────────────────────────────────────────────── */
function getPersonas() {
  const set = new Set();
  (MASTER_DATA || []).forEach(p => {
    (p.equipo || []).forEach(nombre => {
      if (nombre) set.add(nombre);
    });
  });
  return [...set].sort();
}

/* ──────────────────────────────────────────────
   HELPERS DE ESTILO
   ────────────────────────────────────────────── */
function deptCls(dpto) {
  if (!dpto) return '';
  const d = dpto.toLowerCase();
  if (d.includes('vivienda'))     return 'dept-viv';
  if (d.includes('restaurante'))  return 'dept-rest';
  if (d.includes('hotel'))        return 'dept-hot';
  return '';
}

function atencionCls(nivel) {
  const n = (nivel || '').toLowerCase().replace(/\s+/g, '-');
  if (n.includes('maxima') || n.includes('máxima')) return 'risk-high';
  if (n.includes('alta'))                            return 'risk-med';
  if (n.includes('seguimiento'))                     return 'risk-low';
  if (n.includes('estable'))                         return 'risk-ok';
  return 'risk-none';
}

function atencionLbl(nivel) {
  return nivel || '—';
}

function phaseCls(fase) {
  if (!fase) return '';
  const f = fase.toLowerCase();
  if (f.includes('proy'))   return 'phase-proy';
  if (f.includes('obra'))   return 'phase-obra';
  if (f.includes('montaj')) return 'phase-mont';
  if (f.includes('cerrad')) return 'phase-cerr';
  return '';
}

function phaseShort(fase) {
  if (!fase) return '—';
  if (fase.length <= 10) return fase;
  return fase.slice(0, 9) + '…';
}

function tagDept(dpto) {
  return `<span class="tag-dept ${deptCls(dpto)}">${dpto || '—'}</span>`;
}

function tagAtencion(nivel) {
  return `<span class="tag-risk ${atencionCls(nivel)}">${atencionLbl(nivel)}</span>`;
}

/* ──────────────────────────────────────────────
   GANTT — VISTA GENERAL (ventana deslizante de 12 semanas)
   ────────────────────────────────────────────── */
const GENERAL_WEEKS = 12; // semanas visibles en vista general

function semanaWindow() {
  const semanas = PLANNING_DATA?.semanas || [];
  const hoyIdx = semanas.indexOf(hoySemana());
  if (semanas.length === 0) return [];
  const start = Math.max(0, hoyIdx);
  return semanas.slice(start, start + GENERAL_WEEKS);
}

/* Renderiza Gantt para la ventana de vista general */
function renderGanttGeneral(proj) {
  const ventana   = semanaWindow();
  const planProj  = proj._plan;
  if (!ventana.length) return '<div class="gantt-empty">Sin datos</div>';

  const hoy = hoySemana();
  let html = '<div class="gantt-row">';

  ventana.forEach(sem => {
    const esHoy  = sem === hoy;
    const entry  = planProj?.timeline.find(t => t.semana === sem);
    const tieneActividad = entry && entry.actividades && entry.actividades.length > 0;
    let cls = 'gantt-cell';
    if (esHoy) cls += ' gantt-today';
    if (tieneActividad) {
      const nivel = entry.actividades[0].nivel;
      cls += nivel === 'principal' ? ' gantt-active' : ' gantt-sec';
    }
    const titulo = tieneActividad
      ? entry.actividades.map(a => a.texto).join(' / ')
      : '';
    html += `<div class="${cls}" title="${esHoy ? '▶ ' : ''}${sem}${titulo ? ': ' + titulo : ''}" data-sem="${sem}" data-id="${proj.id}"></div>`;
  });

  html += '</div>';
  return html;
}

/* Renderiza Gantt completo para modal de proyecto (todas las semanas con datos) */
function renderGanttCompleto(proj) {
  const planProj = proj._plan;
  const todasSemanas = PLANNING_DATA?.semanas || [];
  if (!todasSemanas.length) return '<div class="gantt-empty">Sin datos de planning</div>';

  const hoy = hoySemana();

  // Determinar rango con actividad (o mostrar todo si no hay)
  const semanasConActividad = new Set(
    (planProj?.timeline || []).map(t => t.semana)
  );
  const semanas = todasSemanas; // todas — continuidad garantizada

  let html = '<div class="gantt-full">';
  html += '<div class="gantt-labels">';
  semanas.forEach(s => {
    html += `<div class="gantt-label${s === hoy ? ' gantt-today-label' : ''}">${s}</div>`;
  });
  html += '</div><div class="gantt-row">';

  semanas.forEach(sem => {
    const esHoy  = sem === hoy;
    const entry  = planProj?.timeline.find(t => t.semana === sem);
    const tieneActividad = entry && entry.actividades && entry.actividades.length > 0;
    let cls = 'gantt-cell';
    if (esHoy) cls += ' gantt-today';
    if (tieneActividad) {
      const nivel = entry.actividades[0].nivel;
      cls += nivel === 'principal' ? ' gantt-active' : ' gantt-sec';
    }
    const titulo = tieneActividad
      ? entry.actividades.map(a => a.texto).join(' / ')
      : (semanasConActividad.size > 0 && !tieneActividad ? 'sin actividad registrada' : '');
    html += `<div class="${cls}" title="${esHoy ? '▶ ' : ''}${sem}${titulo ? ': ' + titulo : ''}"></div>`;
  });

  html += '</div></div>';
  return html;
}

/* ──────────────────────────────────────────────
   TARJETA DE PROYECTO (lista)
   ────────────────────────────────────────────── */
function projCard(proj, opts = {}) {
  const g = proj._global;
  const done = S.get(proj.id, 'done') === '1';

  const atencion   = g?.atencion     || '';
  const bloqueador = g?.bloqueador   || '';
  const hito       = g?.proximo_hito || '';
  const fechaHito  = g?.fecha_hito   || '';

  const ganttHtml = opts.showGantt !== false
    ? `<div class="proj-gantt">${renderGanttGeneral(proj)}</div>`
    : '';

  const equipoHtml = (proj.equipo || []).length
    ? `<div class="proj-equipo">${proj.equipo.map(e => `<span class="tag-persona">${e}</span>`).join(' ')}</div>`
    : '';

  const bloqHtml = bloqueador
    ? `<div class="proj-bloq">⚠ ${bloqueador}</div>`
    : '';

  const hitoHtml = hito
    ? `<div class="proj-hito">→ ${hito}${fechaHito ? ' <em>' + fechaHito + '</em>' : ''}</div>`
    : '';

  return `
    <div class="proj-card ${done ? 'proj-done' : ''} ${atencionCls(atencion)}" data-id="${proj.id}">
      <div class="proj-header">
        <div class="proj-meta">
          ${tagDept(proj.dpto)}
          ${tagAtencion(atencion)}
          <span class="tag-phase ${phaseCls(proj.fase)}">${phaseShort(proj.fase)}</span>
        </div>
        <div class="proj-actions">
          <button class="btn-done" data-id="${proj.id}" title="Marcar completado">
            ${done ? '✓' : '○'}
          </button>
          <button class="btn-open" data-id="${proj.id}" title="Abrir ficha">↗</button>
        </div>
      </div>
      <div class="proj-nombre" data-id="${proj.id}">${proj.nombre}</div>
      ${hitoHtml}
      ${bloqHtml}
      ${equipoHtml}
      ${ganttHtml}
      <div class="proj-note-wrap">
        <textarea class="proj-note" data-id="${proj.id}" placeholder="Nota…" rows="1">${S.get(proj.id, 'note')}</textarea>
      </div>
    </div>`;
}

/* ──────────────────────────────────────────────
   MODAL DE PROYECTO (ficha completa)
   ────────────────────────────────────────────── */
let _modalId = null;

function openModal(id) {
  const proj = enrich(MASTER_DATA.find(p => p.id === id));
  if (!proj) return;
  _modalId = id;

  const g = proj._global;
  const plan = proj._plan;

  const equipoHtml = (proj.equipo || []).map(e =>
    `<span class="tag-persona">${e} <small>(${cargaPersona(e)} proy)</small></span>`
  ).join(' ');

  const actividadesHtml = (plan?.timeline || []).length
    ? plan.timeline.map(t => `
        <div class="plan-semana">
          <span class="plan-sem-lbl ${t.semana === hoySemana() ? 'plan-hoy' : ''}">${t.semana}</span>
          ${t.actividades.map(a =>
            `<span class="plan-act ${a.nivel === 'principal' ? 'plan-principal' : 'plan-sec'}">${a.texto}</span>`
          ).join('')}
        </div>`).join('')
    : '<p class="plan-empty">Sin actividad registrada en planning.</p>';

  const bloqueadorHtml = g?.bloqueador
    ? `<div class="modal-bloq">⚠ Bloqueador: ${g.bloqueador}</div>` : '';

  document.getElementById('modal-title').textContent = proj.nombre;
  document.getElementById('modal-body').innerHTML = `
    <div class="modal-section">
      <div class="modal-tags">
        ${tagDept(proj.dpto)}
        ${tagAtencion(g?.atencion)}
        <span class="tag-phase ${phaseCls(proj.fase)}">${proj.fase || '—'}</span>
      </div>
    </div>

    ${bloqueadorHtml}

    <div class="modal-grid">
      <div class="modal-field">
        <label>Próximo hito</label>
        <span>${g?.proximo_hito || '—'}</span>
      </div>
      <div class="modal-field">
        <label>Fecha hito</label>
        <span>${g?.fecha_hito || '—'}</span>
      </div>
      <div class="modal-field">
        <label>Constructora</label>
        <span>${proj.constructora || '—'}</span>
      </div>
      <div class="modal-field">
        <label>Fin obra previsto</label>
        <span>${proj.fin_obra || '—'}</span>
      </div>
      <div class="modal-field">
        <label>Montaje</label>
        <span>${proj.montaje || '—'}</span>
      </div>
      <div class="modal-field">
        <label>Finalización oficial</label>
        <span>${proj.fin_oficial || '—'}</span>
      </div>
    </div>

    <div class="modal-field">
      <label>Equipo</label>
      <div>${equipoHtml || '—'}</div>
    </div>

    ${proj.obs ? `<div class="modal-field"><label>Observaciones</label><span>${proj.obs}</span></div>` : ''}

    <div class="modal-section">
      <h3>Planning completo</h3>
      <div class="gantt-completo-wrap">
        ${renderGanttCompleto(proj)}
      </div>
      <div class="plan-actividades">${actividadesHtml}</div>
    </div>

    <div class="modal-section">
      <label>Nota personal</label>
      <textarea class="modal-note" data-id="${proj.id}" rows="3" placeholder="Nota privada (solo en este dispositivo)…">${S.get(proj.id, 'note')}</textarea>
    </div>
  `;

  document.getElementById('proj-modal').classList.remove('hidden');
}

function closeModal() {
  // Guardar nota antes de cerrar
  const ta = document.querySelector('.modal-note');
  if (ta && _modalId) S.set(_modalId, 'note', ta.value);
  document.getElementById('proj-modal').classList.add('hidden');
  _modalId = null;
}

/* ──────────────────────────────────────────────
   VISTA JAVI / PM
   Agrupado por dpto, con Gantt general visible
   Incluye: todos los proyectos, alerta de bloqueadores
   ────────────────────────────────────────────── */
function renderJavi() {
  const dptos = ['vivienda', 'restaurantes', 'hoteles'];
  let html = '';

  // Resumen de bloqueadores
  const bloqueados = (MASTER_DATA || []).filter(p => globalOf(p.id)?.bloqueador);
  if (bloqueados.length) {
    html += `<div class="alert-bar">
      <strong>⚠ Bloqueadores activos (${bloqueados.length}):</strong>
      ${bloqueados.map(p => `<span class="alert-item" data-id="${p.id}">${p.nombre}</span>`).join(', ')}
    </div>`;
  }

  // Semana actual destacada
  html += `<div class="week-banner">Semana actual: <strong>${hoySemana()}</strong></div>`;

  dptos.forEach(dpto => {
    const proyectos = (MASTER_DATA || [])
      .filter(p => p.dpto === dpto)
      .map(enrich);

    if (!proyectos.length) return;

    html += `<div class="dept-section">
      <h2 class="dept-title ${deptCls(dpto)}">${dpto.toUpperCase()}</h2>
      <div class="proj-list">
        ${proyectos.map(p => projCard(p)).join('')}
      </div>
    </div>`;
  });

  document.getElementById('main-content').innerHTML = html || '<p class="empty">Sin proyectos.</p>';
}

/* ──────────────────────────────────────────────
   VISTA ALEJANDRA / CEO
   Solo proyectos con atención MÁXIMA o ALTA
   Hitos próximos + bloqueadores destacados
   Sin Gantt (vista ejecutiva)
   ────────────────────────────────────────────── */
function renderAlejandra() {
  const prioritarios = (MASTER_DATA || [])
    .map(enrich)
    .filter(p => {
      const a = (p._global?.atencion || '').toLowerCase();
      return a.includes('máxima') || a.includes('maxima') || a.includes('alta');
    });

  const proximos = (MASTER_DATA || [])
    .map(enrich)
    .filter(p => p._global?.fecha_hito)
    .sort((a, b) => (a._global.fecha_hito || '') < (b._global.fecha_hito || '') ? -1 : 1)
    .slice(0, 8);

  let html = `<div class="week-banner">Semana actual: <strong>${hoySemana()}</strong></div>`;

  // Proyectos prioritarios
  html += `<div class="ale-section">
    <h2>Atención requerida (${prioritarios.length})</h2>
    <div class="proj-list">
      ${prioritarios.length
        ? prioritarios.map(p => projCard(p, { showGantt: false })).join('')
        : '<p class="empty">Sin proyectos en atención alta.</p>'}
    </div>
  </div>`;

  // Próximos hitos
  if (proximos.length) {
    html += `<div class="ale-section">
      <h2>Próximos hitos</h2>
      <table class="hitos-table">
        <thead><tr><th>Proyecto</th><th>Dpto</th><th>Hito</th><th>Fecha</th></tr></thead>
        <tbody>
          ${proximos.map(p => `
            <tr class="hitos-row" data-id="${p.id}">
              <td>${p.nombre}</td>
              <td>${tagDept(p.dpto)}</td>
              <td>${p._global?.proximo_hito || '—'}</td>
              <td>${p._global?.fecha_hito || '—'}</td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
  }

  document.getElementById('main-content').innerHTML = html;
}

/* ──────────────────────────────────────────────
   VISTA PERSONA (individual — derivada dinámicamente)
   Proyectos donde nombre aparece en equipo
   Gantt general + carga de la semana
   ────────────────────────────────────────────── */
function renderPersona(nombre) {
  const proyectos = (MASTER_DATA || [])
    .filter(p => (p.equipo || []).includes(nombre))
    .map(enrich);

  const carga = cargaPersona(nombre);
  const hoy = hoySemana();

  // Proyectos activos esta semana
  const activos = proyectos.filter(p =>
    (p._plan?.timeline || []).some(t => t.semana === hoy)
  );

  let html = `
    <div class="persona-header">
      <h2>${nombre}</h2>
      <div class="persona-stats">
        <span class="stat">${proyectos.length} proyectos totales</span>
        <span class="stat active">${carga} activos esta semana</span>
      </div>
    </div>`;

  if (activos.length) {
    html += `<div class="dept-section">
      <h3>Esta semana (${hoy})</h3>
      <div class="proj-list">
        ${activos.map(p => projCard(p)).join('')}
      </div>
    </div>`;
  }

  const resto = proyectos.filter(p => !activos.includes(p));
  if (resto.length) {
    html += `<div class="dept-section">
      <h3>Resto de proyectos</h3>
      <div class="proj-list">
        ${resto.map(p => projCard(p, { showGantt: false })).join('')}
      </div>
    </div>`;
  }

  if (!proyectos.length) {
    html += '<p class="empty">Sin proyectos asignados.</p>';
  }

  document.getElementById('main-content').innerHTML = html;
}

/* ──────────────────────────────────────────────
   TABS Y NAVEGACIÓN
   ────────────────────────────────────────────── */
let curTab = 'javi';

function buildTabs() {
  const personas = getPersonas();
  const tabsEl = document.getElementById('tabs');
  if (!tabsEl) return;

  const fixed = [
    { id: 'javi',      label: 'Javi / PM' },
    { id: 'alejandra', label: 'Alejandra' },
  ];

  const personaTabs = personas.map(nombre => ({
    id: 'persona__' + nombre.toLowerCase().replace(/\s+/g, '_'),
    label: nombre,
    nombre
  }));

  const allTabs = [...fixed, ...personaTabs];

  tabsEl.innerHTML = allTabs.map(t =>
    `<button class="tab-btn ${t.id === curTab ? 'active' : ''}" data-tab="${t.id}">${t.label}</button>`
  ).join('');
}

function activateTab(tabId) {
  curTab = tabId;

  // Actualizar estado visual
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });

  // Renderizar contenido
  if (tabId === 'javi') {
    renderJavi();
  } else if (tabId === 'alejandra') {
    renderAlejandra();
  } else if (tabId.startsWith('persona__')) {
    // Recuperar nombre original de MASTER_DATA
    const personas = getPersonas();
    const slug = tabId.replace('persona__', '');
    const nombre = personas.find(n =>
      n.toLowerCase().replace(/\s+/g, '_') === slug
    );
    if (nombre) renderPersona(nombre);
  }
}

/* ──────────────────────────────────────────────
   BÚSQUEDA
   ────────────────────────────────────────────── */
function applySearch(query) {
  const q = query.toLowerCase().trim();
  if (!q) {
    activateTab(curTab);
    return;
  }

  const resultados = (MASTER_DATA || [])
    .map(enrich)
    .filter(p => {
      const g = p._global;
      return (
        p.nombre.toLowerCase().includes(q) ||
        (p.dpto || '').toLowerCase().includes(q) ||
        (p.fase || '').toLowerCase().includes(q) ||
        (g?.atencion || '').toLowerCase().includes(q) ||
        (g?.proximo_hito || '').toLowerCase().includes(q) ||
        (g?.bloqueador || '').toLowerCase().includes(q) ||
        (p.equipo || []).some(e => e.toLowerCase().includes(q))
      );
    });

  document.getElementById('main-content').innerHTML = resultados.length
    ? `<div class="search-results">
        <p class="search-header">${resultados.length} resultado${resultados.length !== 1 ? 's' : ''} para "<strong>${query}</strong>"</p>
        <div class="proj-list">${resultados.map(p => projCard(p)).join('')}</div>
      </div>`
    : `<p class="empty">Sin resultados para "<strong>${query}</strong>"</p>`;
}

/* ──────────────────────────────────────────────
   EXPORTAR RESUMEN
   ────────────────────────────────────────────── */
function exportResumen() {
  const hoy = new Date().toLocaleDateString('es-ES');
  const semana = hoySemana();

  let lines = [
    `RESUMEN POMBO ESTUDIO — ${hoy} (${semana})`,
    '='.repeat(50),
    ''
  ];

  const dptos = ['vivienda', 'restaurantes', 'hoteles'];
  dptos.forEach(dpto => {
    const proyectos = (MASTER_DATA || []).filter(p => p.dpto === dpto);
    if (!proyectos.length) return;
    lines.push(`\n── ${dpto.toUpperCase()} (${proyectos.length}) ──`);
    proyectos.forEach(p => {
      const g = globalOf(p.id);
      lines.push(`  ${p.nombre}`);
      if (g?.atencion)     lines.push(`    Atención: ${g.atencion}`);
      if (g?.proximo_hito) lines.push(`    Hito: ${g.proximo_hito}${g.fecha_hito ? ' – ' + g.fecha_hito : ''}`);
      if (g?.bloqueador)   lines.push(`    ⚠ ${g.bloqueador}`);
    });
  });

  const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `pombo_resumen_${semana.replace('/', '-')}.txt`;
  a.click();
}

/* ──────────────────────────────────────────────
   EVENTOS
   ────────────────────────────────────────────── */
function wireEvents() {
  // Tabs
  document.getElementById('tabs')?.addEventListener('click', e => {
    const btn = e.target.closest('.tab-btn');
    if (btn) activateTab(btn.dataset.tab);
  });

  // Búsqueda
  const searchEl = document.getElementById('search-input');
  if (searchEl) {
    let debounce;
    searchEl.addEventListener('input', e => {
      clearTimeout(debounce);
      debounce = setTimeout(() => applySearch(e.target.value), 250);
    });
  }

  // Clic en contenido principal (delegado)
  document.getElementById('main-content')?.addEventListener('click', e => {
    // Abrir modal
    const btnOpen = e.target.closest('.btn-open');
    if (btnOpen) { openModal(btnOpen.dataset.id); return; }

    // Abrir modal al hacer click en nombre
    const nombre = e.target.closest('.proj-nombre');
    if (nombre) { openModal(nombre.dataset.id); return; }

    // Toggle done
    const btnDone = e.target.closest('.btn-done');
    if (btnDone) {
      const id = btnDone.dataset.id;
      const isDone = S.toggle(id, 'done');
      btnDone.textContent = isDone ? '✓' : '○';
      btnDone.closest('.proj-card')?.classList.toggle('proj-done', isDone);
      return;
    }

    // Abrir modal desde alerta/hito
    const alertItem = e.target.closest('.alert-item, .hitos-row');
    if (alertItem?.dataset.id) { openModal(alertItem.dataset.id); return; }
  });

  // Guardar notas (delegado)
  document.getElementById('main-content')?.addEventListener('change', e => {
    const ta = e.target.closest('.proj-note');
    if (ta) S.set(ta.dataset.id, 'note', ta.value);
  });

  // Modal: cerrar
  document.getElementById('modal-close')?.addEventListener('click', closeModal);
  document.getElementById('proj-modal')?.addEventListener('click', e => {
    if (e.target === document.getElementById('proj-modal')) closeModal();
  });

  // Modal: guardar nota al cambiar
  document.getElementById('modal-body')?.addEventListener('change', e => {
    const ta = e.target.closest('.modal-note');
    if (ta && _modalId) S.set(_modalId, 'note', ta.value);
  });

  // Exportar
  document.getElementById('btn-export')?.addEventListener('click', exportResumen);

  // ESC cierra modal
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeModal();
  });
}

/* ──────────────────────────────────────────────
   INIT
   ────────────────────────────────────────────── */
function init() {
  buildIndexes();
  buildTabs();
  wireEvents();
  activateTab('javi');

  // Info de actualización
  const updEl = document.getElementById('updated-at');
  if (updEl && META?.updated) {
    updEl.textContent = 'Actualizado: ' + META.updated.replace('T', ' ').slice(0, 16);
  }
}

document.addEventListener('DOMContentLoaded', init);
