





let curPerson = 'javi';
let filterDept = 'todos', filterRisk = 'todos', filterSearch = '';


// APDS PM Estudio — Lógica de la app

// ── HELPERS ──────────────────────────────────────────────────────────────────
function deptCls(d){
  d=(d||'').toLowerCase();
  if(d.includes('vivienda')) return 'tag-viv';
  if(d.includes('hotel')) return 'tag-hot';
  if(d.includes('restaurante')||d.includes('rest')) return 'tag-rest';
  return 'tag-out';
}
function riskCls(r){
  r=(r||'').toUpperCase();
  if(r.includes('CRITICO')||r.includes('CRÍTICO')||r.includes('MUY ALTO')) return 'tag-crit';
  if(r==='ALTO') return 'tag-alto';
  if(r==='MEDIO') return 'tag-med';
  if(r==='BAJO') return 'tag-baj';
  if(r.includes('VACACIONES')) return 'tag-vac';
  return 'tag-out';
}
function riskLbl(r){
  r=(r||'').toUpperCase();
  if(r.includes('CRITICO')||r.includes('CRÍTICO')||r.includes('MUY ALTO')) return 'Crítico';
  if(r==='ALTO') return 'Alto';
  if(r==='MEDIO') return 'Medio';
  if(r==='BAJO') return 'Bajo';
  if(r.includes('VACACIONES')) return 'Vacaciones';
  return r;
}
function phaseCls(p){
  if(!p) return '';
  const up = p.toUpperCase();
  if(up.includes('PROYECTO')||up.includes('ANTEPROYECTO')||up.includes('PROY')||up.includes('BASICO')||up.includes('PRESUPUESTO')||up.includes('VALORACION')||up.includes('FEEDBACK')||up.includes('RENDER')||up.includes('REUNION')||up.includes('REUNIÓN')||up.includes('IDEAS')||up.includes('MARKETING')||up.includes('EMPEZAR')) return 'ph1';
  if(up.includes('OBRA')||up.includes('EJECUCION')||up.includes('INICIO')||up.includes('EMPIEZA')||up.includes('OBRA DE NUEVO')) return 'ph2';
  if(up.includes('PEDIDO')||up.includes('CARPINTER')||up.includes('CERRAR DECO')||up.includes('TECHOS')||up.includes('REVISAR EQUIPAMIENTO')) return 'ph3';
  if(up.includes('MONTAJE')||up.includes('VISITA')) return 'ph4';
  if(up.includes('ENTREGA')||up.includes('FIN OBRA')||up.includes('CIERRE')||up.includes('TERMINAD')) return 'ph6';
  if(up.includes('RENDERS')||up.includes('DECO')) return 'ph7';
  if(up.includes('PARADO')||up.includes('PENDIENTE')||up.includes('LICENCIA')||up.includes('REPLANTEO')) return 'ph9';
  return 'ph5';
}
function phaseShort(p){
  if(!p) return '';
  const up = p.toUpperCase();
  if(up.includes('MONTAJE')) return 'MONT';
  if(up.includes('ANTEPROYECTO')) return 'ANT';
  if(up.includes('PROY BASICO')||up.includes('PROYECTO BASICO')) return 'PB';
  if(up.includes('PROYECTO')||up.includes('PROY')) return 'PROY';
  if(up.includes('PRESUPUESTO')||up.includes('PRESU')) return 'PRES';
  if(up.includes('VALORACION')||up.includes('VALORACIÓN')) return 'VAL';
  if(up.includes('OBRA')) return 'OBRA';
  if(up.includes('PEDIDO')) return 'PED';
  if(up.includes('CARPINTER')) return 'CARP';
  if(up.includes('REUNIÓN')||up.includes('REUNION')) return 'REUN';
  if(up.includes('ENTREGA')) return 'ENT';
  if(up.includes('RENDERS')||up.includes('RENDER')) return 'REND';
  if(up.includes('DECO')&&!up.includes('INICIO')) return 'DECO';
  if(up.includes('VISITA')) return 'VIS';
  if(up.includes('FIN OBRA')) return 'FIN';
  if(up.includes('CIERRE')||up.includes('CERRAR')) return 'CIE';
  if(up.includes('PARADO')) return '—';
  if(up.includes('PENDIENTE')) return 'PEN';
  if(up.includes('LICENCIA')) return 'LIC';
  if(up.includes('FEEDBACK')) return 'FB';
  if(up.includes('EMPEZAR')||up.includes('EMPIEZA')) return 'INI';
  if(up.includes('REPLANTEO')) return 'REP';
  return p.slice(0,4).toUpperCase();
}

// ── STORAGE ──────────────────────────────────────────────────────────────────
const S = {
  _c: {},
  load(id){
    if(this._c[id]) return this._c[id];
    let v = {check:{}, notes:{}};
    try{ const ls = localStorage.getItem('apds:'+id); if(ls) v=JSON.parse(ls); }catch(e){}
    this._c[id] = v; return v;
  },
  save(id){
    try{ localStorage.setItem('apds:'+id, JSON.stringify(this._c[id])); setSyncStatus('ok'); }catch(e){ setSyncStatus('error'); }
  },
  setCheck(id, k, v){ if(!this._c[id]) this._c[id]={check:{},notes:{}}; this._c[id].check[k]=v; this.save(id); },
  setNote(id, k, v){ if(!this._c[id]) this._c[id]={check:{},notes:{}}; this._c[id].notes[k]=v; this.save(id); },
};

function setSyncStatus(s){
  const el=document.getElementById('sync'); if(!el) return;
  el.className='sync '+(s==='saving'?'saving':s==='error'?'error':'');
  const dot=el.querySelector('.sync-dot'); if(dot) dot.className='sync-dot';
  el.innerHTML=`<span class="sync-dot"></span>${s==='saving'?'Guardando…':s==='error'?'Sin conexión':'Sincronizado'}`;
}

// ── GANTT ──────────────────────────────────────────────────────────────────
function renderGantt(proj, personId){
  const tl = proj.tl || {};
  const slug = proj.slug || proj.nombre.replace(/\s+/g,'_').toLowerCase();
  const state = S._c[personId] || {check:{}, notes:{}};

  // Cabecera meses
  let monthsHtml = '';
  MONTHS.forEach(([m, start, end]) => {
    const span = end - start + 1;
    monthsHtml += `<div class="gantt-month" style="grid-column:span ${span}">${m}</div>`;
  });
  // rellenar hasta 20
  const filled = MONTHS.reduce((a,[,s,e])=>a+(e-s+1),0);
  if(filled < 20) monthsHtml += `<div class="gantt-month" style="grid-column:span ${20-filled}"></div>`;

  // Celdas
  let cells = '';
  const phases = Array.from({length:20},(_,i)=>tl[i]||null);
  for(let i=0;i<20;i++){
    const ph = phases[i];
    const nextPh = phases[i+1];
    const cls = ph ? `gantt-cell filled ${phaseCls(ph)}` : 'gantt-cell';
    const noteKey = `cn:${slug}:${i}`;
    const hasNote = !!(state.notes && state.notes[noteKey]);
    const arrow = ph && nextPh && phaseCls(ph) !== phaseCls(nextPh) ? '<span class="gantt-arrow"></span>' : '';
    const lbl = ph ? `<span class="gantt-label">${phaseShort(ph)}</span>` : '';
    const noteClass = hasNote ? ' has-note' : '';
    cells += ph
      ? `<div class="${cls}${noteClass}" title="${ph} · sem ${WEEK_LABELS[i]}" data-slug="${slug}" data-week="${i}" data-phase="${ph}" data-person="${personId}" data-notekey="${noteKey}">${lbl}${arrow}</div>`
      : `<div class="${cls}" title="Sem ${WEEK_LABELS[i]}"></div>`;
  }

  // Weeks
  const weeksHtml = WEEK_LABELS.map(w=>`<div class="gantt-week">${w}</div>`).join('');
  const todayPct = (TODAY_WEEK / 20 * 100).toFixed(2);

  return `<div class="gantt">
    <div class="gantt-months" style="display:grid;grid-template-columns:repeat(20,1fr);gap:1px;margin-bottom:3px;">${monthsHtml}</div>
    <div class="gantt-row" onclick="openGanttModal(MASTER.find(p=>p.nombre===${JSON.stringify(proj.nombre)})||proj)" style="cursor:pointer;" title="Clic para ver planificación completa">
      <div class="gantt-today" style="left:${todayPct}%"></div>
      <div class="gantt-today-lbl" style="left:calc(${todayPct}% + 3px)">HOY</div>
      <div class="gantt-grid">${cells}</div>
      <div style="text-align:right;font-size:9px;color:var(--cop);margin-top:2px;letter-spacing:.06em;">↗ Ver planificación completa</div>
    </div>
    <div class="gantt-weeks" style="display:grid;grid-template-columns:repeat(20,1fr);gap:1px;margin-top:2px;">${weeksHtml}</div>
  </div>`;
}

// ── MODAL NOTA DE CELDA ────────────────────────────────────────────────────
function openCellModal(slug, weekIdx, phase, personId, noteKey){
  const state = S._c[personId] || {check:{},notes:{}};
  const existing = state.notes?.[noteKey] || '';
  const weekLbl = WEEK_LABELS[weekIdx] || weekIdx;

  const bd = document.createElement('div');
  bd.className = 'modal-bg'; bd.id = 'cell-modal-bg';
  bd.innerHTML = `<div class="modal">
    <div class="modal-head">
      <div><div class="modal-title">${slug.replace(/_/g,' ').toUpperCase()} · ${weekLbl}</div><div class="modal-sub">${phase}</div></div>
      <button class="modal-close" id="m-close">×</button>
    </div>
    <div class="modal-body"><textarea id="m-ta" placeholder="Comentario para esta semana…">${existing}</textarea></div>
    <div class="modal-foot">
      ${existing?'<button class="btn-danger left" id="m-del">Borrar</button>':''}
      <button class="btn-ghost" id="m-cancel">Cancelar</button>
      <button class="btn-cop" id="m-save">Guardar</button>
    </div>
  </div>`;
  document.body.appendChild(bd);
  bd.addEventListener('click', e=>{ if(e.target===bd) closeCellModal(); });
  document.getElementById('m-close').onclick = closeCellModal;
  document.getElementById('m-cancel').onclick = closeCellModal;
  document.getElementById('m-save').onclick = ()=>{
    const v = document.getElementById('m-ta').value.trim();
    S.setNote(personId, noteKey, v);
    const cell = document.querySelector(`[data-notekey="${noteKey}"]`);
    if(cell){ v ? cell.classList.add('has-note') : cell.classList.remove('has-note'); }
    closeCellModal();
  };
  const delBtn = document.getElementById('m-del');
  if(delBtn) delBtn.onclick = ()=>{
    S.setNote(personId, noteKey, '');
    const cell = document.querySelector(`[data-notekey="${noteKey}"]`);
    if(cell) cell.classList.remove('has-note');
    closeCellModal();
  };
  document.getElementById('m-ta').focus();
}
function closeCellModal(){ const el=document.getElementById('cell-modal-bg'); if(el) el.remove(); }

// ── COMPONENTES ──────────────────────────────────────────────────────────────
function tagDept(d){
  const cls=deptCls(d), lbl=d||'Todos';
  return `<span class="tag ${cls}"><span class="dot"></span>${lbl}</span>`;
}
function tagRisk(r){
  return `<span class="tag ${riskCls(r)}"><span class="dot"></span>${riskLbl(r)}</span>`;
}
function alertRow(a){
  return `<div style="display:flex;gap:12px;padding:11px 14px;border:1px solid var(--line);border-radius:var(--r);background:var(--surface);margin-bottom:6px;align-items:flex-start;">
    <span style="flex-shrink:0;margin-top:2px;">${tagRisk(a.risk)}</span>
    <div style="flex:1;min-width:0;">
      <span style="font-weight:600;font-size:13px;">${a.proj}</span>
      <span style="font-size:11px;color:var(--ink3);margin-left:6px;">${a.dept} · ${a.resp}</span>
      <div style="font-size:13px;color:var(--ink2);margin-top:2px;">${a.text}</div>
    </div>
    <div style="font-size:11px;color:var(--ink3);white-space:nowrap;flex-shrink:0;padding-top:2px;">${a.fecha}</div>
  </div>`;
}

function projCard(proj, personId){
  const state = S._c[personId] || {check:{},notes:{}};
  const slug = proj.slug || (proj.nombre||'').replace(/\s+/g,'_').toLowerCase();
  const note = state.notes?.['note:'+slug] || '';
  const hasTl = proj.tl && Object.keys(proj.tl).length > 0;
  return `<div class="proj-card">
    <div class="proj-top">
      <div class="proj-name">${proj.nombre||proj.nombre}</div>
      <div class="proj-tags">
        ${proj.dept ? tagDept(proj.dept) : ''}
        ${proj.riesgo||proj.intensidad ? tagRisk(proj.riesgo||proj.intensidad) : ''}
        ${proj.estado ? `<span class="tag tag-out">${proj.estado}</span>` : ''}
      </div>
    </div>
    ${proj.hito ? `<div class="hito-row"><span class="hito-text">${proj.hito}</span></div>` : ''}
    ${proj.obs ? `<div style="font-size:12px;color:var(--ink3);margin-bottom:8px;">${proj.obs}</div>` : ''}
    ${proj.resp ? `<div class="proj-meta"><span class="k">Equipo</span><span>${proj.resp}</span></div>` : ''}
    ${hasTl ? renderGantt({...proj, slug}, personId) : ''}
    <div class="note-area" style="margin-top:${hasTl?'10px':'8px'}">
      <label>Nota del equipo</label>
      <textarea data-note="${slug}" data-person="${personId}" placeholder="Añadir nota…">${note}</textarea>
    </div>
  </div>`;
}

function focusItem(text, id, personId){
  const state = S._c[personId] || {check:{},notes:{}};
  const done = !!(state.check?.[id]);
  return `<div class="focus-item${done?' done':''}">
    <input type="checkbox" data-check="${id}" data-person="${personId}" ${done?'checked':''}>
    <span class="focus-text">${text}</span>
  </div>`;
}

function rendersSection(filterProjs){
  const rows = filterProjs
    ? RENDERS.filter(c=> filterProjs.some(p=> c.proj.toUpperCase().includes(p.toUpperCase().slice(0,6)) || p.toUpperCase().includes(c.proj.toUpperCase().slice(0,6))))
    : RENDERS;
  const others = filterProjs ? RENDERS.filter(c=> !rows.includes(c)) : [];

  const tblRows = (list) => list.map(r=>`<tr>
    <td>${tagRisk(r.riesgo)}</td>
    <td><b>${r.proj}</b><br><span style="font-size:10.5px;color:var(--ink3);">${r.resp}</span></td>
    <td><span class="tag tag-out">${r.fase}</span></td>
    <td style="font-size:12px;">${r.estado}</td>
    <td style="font-size:11px;white-space:nowrap;">${r.comprometida}</td>
    <td style="font-size:11px;white-space:nowrap;${r.realista.startsWith('⚠')?'color:var(--alto);font-weight:500;':''}">${r.realista}</td>
    <td style="font-size:12px;color:var(--ink2);">${r.next}</td>
  </tr>`).join('');
  const tbl = (list) => `<div class="tbl-wrap"><table class="tbl"><thead><tr>
    <th>Prio</th><th>Proyecto</th><th>Fase</th><th>Estado</th><th>Comprometida</th><th>Realista</th><th>Próximo paso</th>
  </tr></thead><tbody>${tblRows(list)}</tbody></table></div>`;

  return `<div class="panel">
    <div class="panel-head"><span class="eyebrow">Renders — Challan</span><span class="panel-note">${RENDERS.length} proyectos en cola</span></div>
    <div style="margin-bottom:10px;padding:8px 12px;background:var(--alto-t);border-radius:var(--r);font-size:12px;color:var(--alto);font-weight:500;">${CHALLAN_VAC}</div>
    ${filterProjs && rows.length ? `<div style="font-size:10px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;color:var(--ink3);margin-bottom:6px;">Mis proyectos en Challan</div>` : ''}
    ${(filterProjs && rows.length) ? tbl(rows) : tbl(RENDERS)}
    ${others.length ? `<details class="collapse" style="margin-top:8px;"><summary>Resto de la cola (${others.length} proyectos)</summary><div class="inner">${tbl(others)}</div></details>` : ''}
    <div style="margin-top:10px;padding:12px 14px;background:var(--cop3);border-radius:var(--r);border:1px dashed var(--cop);">
      <div style="font-size:10.5px;font-weight:500;letter-spacing:.1em;text-transform:uppercase;color:var(--cop);margin-bottom:8px;">+ Solicitar render a Challan</div>
      <div class="challan-form">
        <div><label>Proyecto</label><input id="ch-proj" type="text" placeholder="Nombre del proyecto"></div>
        <div><label>Fase</label><select id="ch-fase"><option>F1 — Volumetría y capturas</option><option>F2 — Materialidad y acabados</option><option>F3 — Render final</option></select></div>
        <div><label>Documentación disponible</label><input id="ch-doc" type="text" placeholder="Planos, 3D, vistas marcadas…"></div>
        <div><label>Fecha comprometida con cliente</label><input id="ch-fecha" type="text" placeholder="ej. 22 jun"></div>
        <div><label>Notas adicionales</label><textarea id="ch-notas" rows="2" style="min-height:0;" placeholder="Contexto, prioridad, solapamientos…"></textarea></div>
        <button class="btn-cop" id="ch-submit">Enviar solicitud al PM</button>
        <div id="ch-msg" style="font-size:12px;color:var(--baj);display:none;">✅ Solicitud registrada — el PM la revisará y la añadirá a la cola</div>
      </div>
    </div>
    <details class="collapse" style="margin-top:8px;"><summary>Flujo Challan · F1 → F2 → F3</summary>
      <div class="inner" style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:4px;">
        ${CHALLAN_FLUJO.map(f=>`<div style="background:var(--paper);border:1px solid var(--line);border-radius:var(--r);padding:10px 12px;">
          <div style="font-size:10px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--cop);margin-bottom:4px;">${f.fase}</div>
          <div style="font-size:12px;font-weight:500;margin-bottom:4px;">${f.titulo}</div>
          <div style="font-size:11.5px;color:var(--ink3);line-height:1.5;">${f.desc}</div>
        </div>`).join('')}
      </div>
    </details>
    <details class="collapse" style="margin-top:6px;"><summary>Reglas operativas Challan</summary>
      <div class="inner">${CHALLAN_REGLAS.map((r,i)=>`<div style="font-size:12px;color:var(--ink2);padding:5px 0;border-bottom:1px solid var(--paper2);">${i+1}. ${r}</div>`).join('')}</div>
    </details>
  </div>`;
}

// ── VISTAS ────────────────────────────────────────────────────────────────────
curPerson = 'javi';
filterDept = 'todos', filterRisk = 'todos', filterSearch = '';

function renderMaster(){
  const st=S._c['javi']||{check:{},notes:{}};
  let h='';

  h+=`<div class="view-head">
    <div><div class="view-title">Javi · Master</div><div class="view-sub">${WEEK_LABEL}</div></div>
    <div class="view-tags">${tagDept('Vivienda')}${tagDept('Hoteles')}${tagDept('Restaurantes')}</div>
  </div>`;

  // MI FOCO ESTA SEMANA
  if((FOCO_SEMANA.javi||[]).length){
    h+=`<div class="panel"><div class="panel-head"><span class="eyebrow">Mi foco esta semana</span></div>
      <div class="focus-list">${(FOCO_SEMANA.javi||[]).map((t,i)=>focusItem(t,'javi-f'+i,'javi')).join('')}</div></div>`;
  }

  // ESTA SEMANA EN EL ESTUDIO
  h+=`<div class="panel"><div class="panel-head"><span class="eyebrow">Esta semana en el estudio</span></div>
    <div class="agenda-box">${AGENDA.map(a=>`<div class="agenda-row"><span class="agenda-when">${a.when}</span><span>${a.text}</span></div>`).join('')}</div></div>`;

  // MONTAJES
  h+=`<div class="panel"><div class="panel-head"><span class="eyebrow">Montajes confirmados</span></div>
    <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Fechas</th><th>Proyecto</th><th>Equipo</th><th>Dpto</th></tr></thead><tbody>
    ${MONTAJES.map(m=>`<tr><td style="font-size:11px;white-space:nowrap;">${m.fechas}</td><td><b>${m.proj}</b></td><td>${m.equipo}</td><td>${tagDept(m.dept)}</td></tr>`).join('')}
    </tbody></table></div></div>`;

  // MASTER GLOBAL POR RIESGO CON GANTT
  const niveles = ['ATENCIÓN MÁXIMA','ATENCIÓN ALTA','SEGUIMIENTO','ESTABLE'];
  const labelNivel = {'ATENCIÓN MÁXIMA':'Atención Máxima','ATENCIÓN ALTA':'Atención Alta','SEGUIMIENTO':'Seguimiento','ESTABLE':'Estable'};
  const clsNivel = {'ATENCIÓN MÁXIMA':'tag-crit','ATENCIÓN ALTA':'tag-alto','SEGUIMIENTO':'tag-med','ESTABLE':'tag-baj'};

  h+=`<div class="panel"><div class="panel-head"><span class="eyebrow">Master global — por prioridad</span><span class="panel-note">${MASTER.length} proyectos</span></div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;align-items:center;">
      <input type="text" id="m-search" placeholder="Buscar…" style="font-family:var(--f);font-size:12.5px;padding:7px 12px;border:1px solid var(--line);border-radius:999px;background:var(--surface);color:var(--ink);min-width:160px;">
    </div>`;

  niveles.forEach(nivel => {
    const projs = MASTER.filter(p=>p.nivel===nivel);
    if(!projs.length) return;
    h+=`<div style="margin-bottom:20px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <span class="tag ${clsNivel[nivel]||'tag-out'}"><span class="dot"></span>${labelNivel[nivel]||nivel}</span>
        <span style="font-size:11px;color:var(--ink3);">${projs.length} proyectos</span>
      </div>`;

    projs.forEach(p => {
      const slug = p.nombre.replace(/\s+/g,'_').toLowerCase();
      const hasTl = p.tl && Object.keys(p.tl).length>0;
      const note = st.notes?.['note:'+slug]||'';
      h+=`<div class="proj-card">
        <div class="proj-top">
          <div class="proj-name">${p.nombre}</div>
          <div class="proj-tags">${p.dept?tagDept(p.dept):''}${p.fase?`<span class="tag tag-out">${p.fase}</span>`:''}</div>
        </div>
        ${p.hito&&p.hito!=='—'?`<div class="hito-row"><span class="hito-text">${p.hito}</span><span class="hito-date" style="margin-left:8px;">${p.fecha||''}</span></div>`:''}
        ${p.resp&&p.resp!=='—'?`<div class="proj-meta"><span class="k">Equipo</span><span>${p.resp}</span></div>`:''}
        ${p.bloqueador&&p.bloqueador!=='—'?`<div style="font-size:12px;color:var(--crit);margin-bottom:6px;">⚠ ${p.bloqueador}</div>`:''}
        ${hasTl?renderGantt({...p,slug},'javi'):''}
        <div class="note-area" style="margin-top:8px;"><label>Nota</label>
          <textarea data-note="${slug}" data-person="javi" placeholder="Añadir nota…">${note}</textarea>
        </div>
      </div>`;
    });
    h+='</div>';
  });

  h+='</div>';
  return h;
}

function renderMasterTable(){
  const q = filterSearch.toLowerCase();
  const rows = MASTER.filter(p=>{
    if(filterDept!=='todos'){
      const d=DEPT_PERSONA; // rough dept from resp
      const resp=(p.resp||'').toLowerCase();
      if(filterDept==='Vivienda' && !['alicia','olatz','paula','sara','andrea','cristina','nela'].some(n=>resp.includes(n)) && !(p.nombre||'').toUpperCase().match(/PEDRAZA|ZAHARA|LAGOS 1|ALCALA|FLORIDA|HERMOSILLA|MONTESQUINZA|RINCONADA|ALDAMA|SANTANDER VIV|IBIZA|VALENCIA|PALOMA|TORRE|TEPEYAC|SUR [37]/)) {/* skip */}
      // simplified: just use intensidad/riesgo filter
    }
    if(filterRisk!=='todos'){
      const rl=riskLbl(p.riesgo);
      if(filterRisk==='Crítico' && !rl.includes('tico')) return false;
      if(filterRisk==='Alto' && rl!=='Alto') return false;
      if(filterRisk==='Medio' && rl!=='Medio') return false;
      if(filterRisk==='Bajo' && rl!=='Bajo') return false;
    }
    if(q && !`${p.nombre} ${p.resp} ${p.estado} ${p.hito} ${p.obs}`.toLowerCase().includes(q)) return false;
    return true;
  });

  const el=document.getElementById('master-tbl'); if(!el) return;
  el.innerHTML=`<div class="tbl-wrap"><table class="tbl"><thead><tr>
    <th>Proyecto</th><th>Responsable</th><th>Estado</th><th>Próximo hito</th><th>Riesgo</th><th>Observaciones</th>
  </tr></thead><tbody>
  ${rows.map(p=>`<tr>
    <td><b>${p.nombre}</b></td>
    <td style="font-size:12px;">${p.resp}</td>
    <td>${p.estado}</td>
    <td style="font-size:12px;">${p.hito}</td>
    <td>${tagRisk(p.riesgo)}</td>
    <td style="font-size:12px;color:var(--ink3);">${p.obs}</td>
  </tr>`).join('')}
  </tbody></table></div><div style="font-size:11px;color:var(--ink3);margin-top:6px;">${rows.length} de ${MASTER.length} proyectos</div>`;
}

function renderAle(){
  let h='';
  h+=`<div class="view-head">
    <div><div class="view-title">Alejandra · CEO</div><div class="view-sub">${WEEK_LABEL} · Resumen ejecutivo</div></div>
    <div class="view-tags"><span class="tag tag-vac"><span class="dot"></span>Vacaciones 3–21 ago</span></div>
  </div>`;

  // 1. MI FOCO (hitos de la semana del Excel)
  h+=`<div class="panel"><div class="panel-head"><span class="eyebrow">Esta semana — hitos</span><span class="panel-note">${ALE_HITOS.length} compromisos</span></div>
    <div class="agenda-box">
    ${ALE_HITOS.map(a=>`<div class="agenda-row">
      <span class="agenda-when">${a.when}</span>
      <div style="flex:1"><b>${a.proj}</b>${a.quien?' · <span style="color:var(--ink3);font-size:12px;">'+a.quien+'</span>':''}<br><span style="font-size:12.5px;color:var(--ink2);">${a.text}</span></div>
    </div>`).join('')}
    </div></div>`;

  // 2. ALERTAS (filtradas del Excel — solo las importantes)
  h+=`<div class="panel"><div class="panel-head"><span class="eyebrow">Alertas — dónde puede necesitar intervenir</span><span class="panel-note">${ALE_ALERTAS.length} activas</span></div>
    ${ALE_ALERTAS.map(a=>`<div style="display:flex;gap:12px;padding:11px 14px;border:1px solid var(--line);border-radius:var(--r);background:var(--surface);margin-bottom:6px;align-items:flex-start;">
      <span style="flex-shrink:0;margin-top:2px;">${tagRisk(a.risk)}</span>
      <div style="flex:1;min-width:0;">
        <span style="font-weight:600;font-size:13px;">${a.proj}</span>
        <span style="font-size:11px;color:var(--ink3);margin-left:6px;">${a.resp}</span>
        <div style="font-size:13px;color:var(--ink2);margin-top:2px;">${a.text}</div>
      </div>
    </div>`).join('')}
  </div>`;

  // 3. MONTAJES
  h+=`<div class="panel"><div class="panel-head"><span class="eyebrow">Montajes confirmados</span></div>
    <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Fechas</th><th>Proyecto</th><th>Equipo</th><th>Notas</th></tr></thead><tbody>
    ${ALE_MONTAJES.map(m=>`<tr>
      <td style="font-size:11px;white-space:nowrap;font-weight:500;color:var(--cop);">${m.fechas}</td>
      <td><b>${m.proj}</b></td>
      <td style="font-size:12px;">${m.equipo}</td>
      <td style="font-size:11.5px;color:var(--ink3);">${m.notas}</td>
    </tr>`).join('')}
    </tbody></table></div></div>`;

  // 4. PRESENCIA COMPROMETIDA
  h+=`<div class="panel"><div class="panel-head"><span class="eyebrow">Tu presencia comprometida</span></div>
    <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Fecha</th><th>Compromiso</th></tr></thead><tbody>
    ${ALE_PRESENCIA.map(p=>`<tr>
      <td style="font-size:11px;white-space:nowrap;font-weight:500;color:var(--cop);">${p.fecha}</td>
      <td>${p.texto}</td>
    </tr>`).join('')}
    </tbody></table></div></div>`;

  // 5. PRÓXIMAS SEMANAS
  h+=`<div class="panel"><div class="panel-head"><span class="eyebrow">Próximas semanas — tener en cuenta</span></div>
    ${ALE_PROXIMAS.map(s=>`<div class="prox-card">
      <div class="prox-head">${s.sem}</div>
      <div class="prox-body">${s.items.map(i=>`<div class="prox-item${i.startsWith('??')?' alert':i.includes('⚠')?' warn':''}">${i}</div>`).join('')}</div>
    </div>`).join('')}
  </div>`;

  return h;
}

function renderPersonal(pid){
  const state = S._c[pid] || {check:{},notes:{}};
  const nombre = NOMBRE_PERSONA[pid]||pid;
  const dept = DEPT_PERSONA[pid]||'';
  const foco = FOCO_SEMANA[pid]||[];
  const projNames = PROJS_PERSONA[pid]||[];
  const isVac = (VAC[pid]||'').includes('15–19 jun');

  let h='';
  h+=`<div class="view-head">
    <div><div class="view-title">${nombre}</div><div class="view-sub">${WEEK_LABEL}</div></div>
    <div class="view-tags">${dept&&dept!=='todos'?tagDept(dept):''}${isVac?'<span class="tag tag-vac"><span class="dot"></span>Vacaciones</span>':''}</div>
  </div>`;

  if(foco.length){
    h+=`<div class="panel"><div class="panel-head"><span class="eyebrow">Foco esta semana</span></div>
      <div class="focus-list">${foco.map((t,i)=>focusItem(t,`${pid}-f${i}`,pid)).join('')}</div></div>`;
  }

  // Alertas relevantes
  const myAlerts = ALERTAS.filter(a=>{
    const text=`${a.resp} ${a.proj} ${a.text}`.toLowerCase();
    return text.includes(nombre.toLowerCase()) || projNames.some(p=>text.includes(p.toLowerCase().slice(0,6)));
  });
  if(myAlerts.length){
    h+=`<div class="panel"><div class="panel-head"><span class="eyebrow">Alertas relevantes</span></div>${myAlerts.map(alertRow).join('')}</div>`;
  }

  // Proyectos
  const myProjs = MASTER.filter(p=> projNames.some(n=> { const pn=p.nombre.toUpperCase(); const nn=n.toUpperCase(); return (nn.length>=8 && pn.startsWith(nn.slice(0,8))) || (pn.length>=8 && nn.startsWith(pn.slice(0,8))) || pn===nn; }));
  if(myProjs.length){
    h+=`<div class="panel"><div class="panel-head"><span class="eyebrow">Mis proyectos</span><span class="panel-note">${myProjs.length} activos</span></div>
      ${myProjs.map(p=>projCard({...p,slug:p.nombre.replace(/\s+/g,'_').toLowerCase()},pid)).join('')}
    </div>`;
  }

  // Challan
  // Renders en pestaña propia

  return h;
}


function rendersSection(filterProjs){
  const rows=filterProjs?RENDERS.filter(c=>filterProjs.some(p=>c.proj.toUpperCase().includes(p.toUpperCase().slice(0,6))||p.toUpperCase().includes(c.proj.toUpperCase().slice(0,6)))):RENDERS;
  const others=filterProjs?RENDERS.filter(c=>!rows.includes(c)):[];
  const tR=list=>list.map(r=>`<tr>
    <td>${tagRisk(r.riesgo)}</td><td><b>${r.proj}</b><br><span style="font-size:10.5px;color:var(--ink3);">${r.resp}</span></td>
    <td><span class="tag tag-out">${r.fase||'—'}</span></td>
    <td style="font-size:12px;">${r.estado||'—'}</td>
    <td style="font-size:11px;white-space:nowrap;">${r.comprometida||'—'}</td>
    <td style="font-size:11px;white-space:nowrap;${(r.realista||'').startsWith('⚠')?'color:var(--alto);font-weight:500;':''}">${r.realista||'—'}</td>
    <td style="font-size:12px;color:var(--ink2);">${r.next||'—'}</td>
  </tr>`).join('');
  const tbl=list=>`<div class="tbl-wrap"><table class="tbl"><thead><tr>
    <th>Prio</th><th>Proyecto</th><th>Fase</th><th>Estado</th><th>Comprometida</th><th>Realista</th><th>Próximo paso</th>
  </tr></thead><tbody>${tR(list)}</tbody></table></div>`;
  return `<div class="panel">
    <div class="panel-head"><span class="eyebrow">Renders — cola y estado</span><span class="panel-note">${RENDERS.length} proyectos</span></div>
    <div style="margin-bottom:10px;padding:8px 12px;background:var(--alto-t);border-radius:var(--r);font-size:12px;color:var(--alto);font-weight:500;">${RENDERS_VAC}</div>
    ${filterProjs&&rows.length?'<div style="font-size:10px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;color:var(--ink3);margin-bottom:6px;">Mis proyectos en cola</div>':''}
    ${filterProjs&&rows.length?tbl(rows):tbl(RENDERS)}
    ${others.length?`<details class="collapse" style="margin-top:8px;"><summary>Resto de la cola (${others.length})</summary><div class="inner">${tbl(others)}</div></details>`:''}
    <details class="collapse" style="margin-top:8px;"><summary>Flujo · F1 → F2 → F3</summary>
      <div class="inner" style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:4px;">
        ${RENDERS_FLUJO.map(f=>`<div style="background:var(--paper);border:1px solid var(--line);border-radius:var(--r);padding:10px 12px;"><div style="font-size:10px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--cop);margin-bottom:4px;">${f.fase}</div><div style="font-size:12px;font-weight:500;margin-bottom:4px;">${f.titulo}</div><div style="font-size:11.5px;color:var(--ink3);line-height:1.5;">${f.desc}</div></div>`).join('')}
      </div>
    </details>
  </div>`;
}

function renderRendersView(){
  let h='';
  h+=`<div class="view-head"><div><div class="view-title">Renders · 3D</div><div class="view-sub">${WEEK_LABEL}</div></div></div>`;
  h+=rendersSection(null);
  return h;
}

// ── RENDER PRINCIPAL ──────────────────────────────────────────────────────────
function render(){
  // Tabs
  const tabLabels = {'javi':'Javi · Master','ale':'Alejandra · CEO'};
  let tabsHtml='';
  // Javi y Ale sin fondo
  ['javi','ale'].forEach(id=>{
    const lbl=tabLabels[id]||NOMBRE_PERSONA[id];
    tabsHtml+=`<button class="tab${id===curPerson?' active':''} tab-master" data-tab="${id}">${lbl}</button>`;
  });
  // Departamentos con fondo de color
  const deptColors={'VIVIENDA':'rgba(61,100,145,0.10)','RESTAURANTES':'rgba(179,93,48,0.10)','HOTELES':'rgba(67,107,58,0.10)'};
  const deptBorders={'VIVIENDA':'rgba(61,100,145,0.25)','RESTAURANTES':'rgba(179,93,48,0.25)','HOTELES':'rgba(67,107,58,0.25)'};
  const deptLbls={'VIVIENDA':'Vivienda','RESTAURANTES':'Restaurantes','HOTELES':'Hoteles'};
  Object.entries(DEPT_SECTIONS).forEach(([dept,pids])=>{
    if(!pids.length)return;
    const bg=deptColors[dept]||'transparent';
    const br=deptBorders[dept]||'var(--line)';
    tabsHtml+=`<span style="display:inline-flex;align-items:center;background:${bg};border-left:2px solid ${br};padding:0 6px 0 8px;margin:4px 0;border-radius:0 3px 3px 0;">`;
    tabsHtml+=`<span style="font-size:8.5px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:${br};margin-right:4px;white-space:nowrap;">${deptLbls[dept]}</span>`;
    pids.forEach(id=>{
      tabsHtml+=`<button class="tab${id===curPerson?' active':''}" data-tab="${id}" style="background:transparent;">${NOMBRE_PERSONA[id]||id}</button>`;
    });
    tabsHtml+=`</span>`;
  });
  // Renders al final
  tabsHtml+=`<button class="tab${curPerson==='renders'?' active':''} tab-master" data-tab="renders" style="margin-left:4px;">Renders</button>`;
  document.getElementById('tabs').innerHTML=tabsHtml;

  document.getElementById('week-badge').textContent = WEEK_STAMP;
  document.getElementById('update-badge').textContent = UPDATED;

  const view = document.getElementById('view');
  if(curPerson==='javi'){
    filterDept='todos'; filterRisk='todos'; filterSearch='';
    view.innerHTML = renderMaster();
    renderMasterTable();
  } else if(curPerson==='ale'){
    view.innerHTML = renderAle();
  } else if(curPerson==='renders'){
    view.innerHTML = renderRendersView();
  } else {
    view.innerHTML = renderPersonal(curPerson);
  }

  wireEvents();
}


function openGanttModal(proj){
  const tl = proj.tl || {};
  const slug = proj.slug || proj.nombre.replace(/\s+/g,'_').toLowerCase();

  // Construir filas del Gantt expandido (20 semanas)
  const MONTH_SPANS = [['MAY',0,1],['JUN',2,5],['JUL',6,10],['AGO',11,14],['SEP',15,18],['OCT',19,19]];
  let monthsHtml = MONTH_SPANS.map(([m,s,e])=>`<div style="grid-column:span ${e-s+1};font-size:9px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--ink3);padding-left:2px;">${m}</div>`).join('');

  let cells = '';
  const phases = Array.from({length:20},(_,i)=>tl[i]||null);
  for(let i=0;i<20;i++){
    const ph=phases[i];
    const cls=ph?`gantt-cell filled ${phaseCls(ph)}`:'gantt-cell';
    const lbl=ph?`<span class="gantt-label">${phaseShort(ph)}</span>`:'';
    cells+=`<div class="${cls}" title="${ph||'—'} · ${WEEK_LABELS[i]}" style="height:32px;">${lbl}</div>`;
  }
  const weeksHtml=WEEK_LABELS.map(w=>`<div style="font-size:7.5px;color:var(--ink3);padding-left:2px;overflow:hidden;white-space:nowrap;">${w}</div>`).join('');
  const todayPct=(TODAY_WEEK/20*100).toFixed(2);

  const bd=document.createElement('div');
  bd.className='modal-bg'; bd.id='gantt-modal-bg';
  bd.innerHTML=`<div class="modal" style="max-width:720px;width:100%;">
    <div class="modal-head">
      <div>
        <div class="modal-title">${proj.nombre}</div>
        <div class="modal-sub">${proj.dept||''} · ${proj.fase||''} · ${proj.resp||''}</div>
      </div>
      <button class="modal-close" id="gm-close">×</button>
    </div>
    <div class="modal-body" style="padding:20px;">
      <!-- GANTT COMPLETO -->
      <div style="margin-bottom:16px;">
        <div style="display:grid;grid-template-columns:repeat(20,1fr);gap:1px;margin-bottom:3px;">${monthsHtml}</div>
        <div style="position:relative;">
          <div style="position:absolute;top:0;bottom:0;left:${todayPct}%;width:2px;background:var(--burg);opacity:.65;z-index:3;pointer-events:none;"></div>
          <div style="display:grid;grid-template-columns:repeat(20,1fr);gap:1px;">${cells}</div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(20,1fr);gap:1px;margin-top:2px;">${weeksHtml}</div>
      </div>
      <!-- DATOS DEL PROYECTO -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:13px;">
        <div>
          <div style="font-size:10px;font-weight:500;letter-spacing:.1em;text-transform:uppercase;color:var(--ink3);margin-bottom:8px;">Información del proyecto</div>
          ${[
            ['Estado',proj.estado],['Fase',proj.fase],['Responsable',proj.resp],
            ['Constructora',proj.constructora],['Próximo hito',proj.hito],
            ['Fecha',proj.fecha]
          ].filter(([,v])=>v&&v!=='—').map(([k,v])=>`
            <div style="display:flex;gap:8px;padding:5px 0;border-bottom:1px solid var(--line);">
              <span style="font-size:10.5px;font-weight:500;letter-spacing:.06em;text-transform:uppercase;color:var(--ink3);width:100px;flex-shrink:0;">${k}</span>
              <span style="color:var(--ink2);">${v}</span>
            </div>`).join('')}
        </div>
        <div>
          <div style="font-size:10px;font-weight:500;letter-spacing:.1em;text-transform:uppercase;color:var(--ink3);margin-bottom:8px;">Riesgos y bloqueadores</div>
          ${proj.bloqueador&&proj.bloqueador!=='—'?`
            <div style="padding:8px 12px;background:var(--crit-t);border-radius:var(--r);font-size:12.5px;color:var(--crit);margin-bottom:8px;">⚠ ${proj.bloqueador}</div>`:'<div style="font-size:12.5px;color:var(--ink3);">Sin bloqueadores activos</div>'}
          ${proj.obs&&proj.obs!==''?`
            <div style="margin-top:8px;">
              <div style="font-size:10px;font-weight:500;letter-spacing:.06em;text-transform:uppercase;color:var(--ink3);margin-bottom:4px;">Observaciones</div>
              <div style="font-size:12.5px;color:var(--ink2);line-height:1.5;">${proj.obs}</div>
            </div>`:''}
        </div>
      </div>
    </div>
    <div class="modal-foot">
      <button class="btn-ghost" id="gm-close2">Cerrar</button>
    </div>
  </div>`;

  document.body.appendChild(bd);
  bd.addEventListener('click',e=>{if(e.target===bd)closeGanttModal();});
  document.getElementById('gm-close').onclick=closeGanttModal;
  document.getElementById('gm-close2').onclick=closeGanttModal;
}

function closeGanttModal(){
  const el=document.getElementById('gantt-modal-bg');
  if(el)el.remove();
}

function phaseShort(p){
  if(!p)return'';
  const u=p.toUpperCase();
  if(u.includes('MONTAJE'))return'MONT';
  if(u.includes('ANTEPROYECTO'))return'ANT';
  if(u.includes('PROY BASICO')||u.includes('PROYECTO BASICO'))return'PB';
  if(u.includes('PROYECTO')||u.includes('PROY'))return'PROY';
  if(u.includes('PRESUPUESTO'))return'PRES';
  if(u.includes('OBRA'))return'OBRA';
  if(u.includes('PEDIDO'))return'PED';
  if(u.includes('REUNIÓN')||u.includes('REUNION'))return'REUN';
  if(u.includes('ENTREGA'))return'ENT';
  if(u.includes('RENDERS')||u.includes('RENDER'))return'REND';
  if(u.includes('DECO'))return'DECO';
  if(u.includes('VISITA'))return'VIS';
  if(u.includes('ALEJANDRA'))return'ALE';
  if(u.includes('FUERA'))return'FUERA';
  return p.slice(0,4).toUpperCase();
}

function wireEvents(){
  // Tabs
  document.querySelectorAll('[data-tab]').forEach(el=>{
    el.addEventListener('click', async ()=>{
      curPerson = el.dataset.tab;
      await S.load(curPerson);
      render();
    });
  });
  // Checkboxes
  document.querySelectorAll('[data-check]').forEach(el=>{
    el.addEventListener('change', ()=>{
      S.setCheck(el.dataset.person, el.dataset.check, el.checked);
      el.closest('.focus-item').classList.toggle('done', el.checked);
    });
  });
  // Notas proyecto
  document.querySelectorAll('[data-note]').forEach(el=>{
    el.addEventListener('change', ()=>{ S.setNote(el.dataset.person, 'note:'+el.dataset.note, el.value); });
  });
  // Celdas Gantt
  document.querySelectorAll('[data-notekey]').forEach(el=>{
    el.addEventListener('click', ()=>{
      openCellModal(el.dataset.slug, parseInt(el.dataset.week), el.dataset.phase, el.dataset.person, el.dataset.notekey);
    });
    const state = S._c[el.dataset.person] || {check:{},notes:{}};
    if(state.notes?.[el.dataset.notekey]) el.classList.add('has-note');
  });
  // Filtros master
  document.querySelectorAll('[data-fdept]').forEach(el=>{
    el.addEventListener('click', ()=>{ filterDept=el.dataset.fdept; renderMasterTable(); });
  });
  document.querySelectorAll('[data-frisk]').forEach(el=>{
    el.addEventListener('click', ()=>{ filterRisk=el.dataset.frisk; renderMasterTable(); });
  });
  const ms=document.getElementById('m-search');
  if(ms) ms.addEventListener('input', ()=>{ filterSearch=ms.value; renderMasterTable(); });
  // Challan request
  const chBtn=document.getElementById('ch-submit');
  if(chBtn) chBtn.addEventListener('click', ()=>{
    const proj=document.getElementById('ch-proj')?.value?.trim();
    if(!proj){ alert('Indica el nombre del proyecto'); return; }
    const key=`challan-req:${Date.now()}`;
    const data={proj, fase:document.getElementById('ch-fase')?.value, doc:document.getElementById('ch-doc')?.value, fecha:document.getElementById('ch-fecha')?.value, notas:document.getElementById('ch-notas')?.value, quien:NOMBRE_PERSONA[curPerson], cuando:new Date().toLocaleString('es-ES')};
    S.setNote('javi', key, JSON.stringify(data));
    document.getElementById('ch-msg').style.display='block';
    ['ch-proj','ch-doc','ch-fecha','ch-notas'].forEach(id=>{ const el=document.getElementById(id); if(el) el.value=''; });
  });
}

// ── EXPORT ───────────────────────────────────────────────────────────────────
document.getElementById('export-btn').addEventListener('click', async ()=>{
  const out={_exported:new Date().toISOString(),_week:WEEK_LABEL,data:{}};
  for(const id of PERSON_ORDER){ await S.load(id); out.data['s:'+id]=S._c[id]; }
  const blob=new Blob([JSON.stringify(out,null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a'); a.href=url; a.download=`pm_estado_${new Date().toISOString().slice(0,10)}.json`;
  document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
});

// ── INIT ─────────────────────────────────────────────────────────────────────
(function init(){
  for(const id of PERSON_ORDER) S.load(id);
  render();
})();







