#!/usr/bin/env python3
"""
APDS PM Estudio — Generador de app v3
Lee PM_ESTUDIO_MASTER_COMPLETO.xlsx y genera docs/index.html
Estructura nueva: MASTER GLOBAL + VIVIENDA/HOTELES/RESTAURANTES (Gantt sep-nov 2026)
"""
import openpyxl, json, os
from datetime import date

BASE  = os.path.dirname(os.path.abspath(__file__))
EXCEL = os.path.join(BASE, 'PM_ESTUDIO_MASTER_COMPLETO.xlsx')
OUT   = os.path.join(BASE, 'docs', 'index.html')

wb = openpyxl.load_workbook(EXCEL, data_only=True)
print("Hojas:", wb.sheetnames)

# ── Semanas: 1 sep → 10 nov 2026 (11 semanas) ────────────────────────────────
hoy = date.today()
sem_inicio = date(2026, 9, 1)
TODAY_WEEK = max(0, min((hoy - sem_inicio).days // 7, 10))
WEEK_LABELS = ['1 SEP','8 SEP','15 SEP','22 SEP','29 SEP',
               '6 OCT','13 OCT','20 OCT','27 OCT','3 NOV','10 NOV']
MONTHS = [["SEP",0,4],["OCT",5,8],["NOV",9,10]]

def find_sheet(*keywords):
    """Busca la primera hoja cuyo nombre contiene TODOS los keywords (si se pasan varios)
    o CUALQUIERA si se usa con un solo keyword."""
    # Primero: coincidencia exacta con nombre completo 'MASTER GLOBAL'
    for s in wb.sheetnames:
        if s.upper() == ' '.join(k.upper() for k in keywords):
            return s
    # Segundo: todas las keywords presentes en el nombre
    if len(keywords) > 1:
        for s in wb.sheetnames:
            if all(k.upper() in s.upper() for k in keywords):
                return s
    # Tercero: cualquier keyword
    for s in wb.sheetnames:
        if any(k.upper() in s.upper() for k in keywords):
            return s
    return None

# ── MASTER GLOBAL ─────────────────────────────────────────────────────────────
# Cols: PROYECTO | DPTO | RESPONSABLE | ESTADO | HITO PRÓXIMO | FECHA |
#       BLOQUEADOR | CONSTRUCTORA | FASE | ATENCIÓN | NIVEL | OBSERVACIONES
def extract_master():
    sheet = find_sheet('MASTER','GLOBAL')
    if not sheet:
        print("⚠ No se encontró hoja MASTER GLOBAL")
        return []
    ws = wb[sheet]
    projects, header = [], False
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=12, values_only=True):
        if not any(c for c in row): continue
        first = str(row[0] or '').strip()
        # Header row detection
        if first == 'PROYECTO':
            header = True; continue
        if not header: continue
        if not row[0] or not isinstance(row[0], str): continue
        n = str(row[0]).strip()
        # Skip section separators and short strings
        if n.startswith('▸') or n.startswith('—') or n.startswith('──') or len(n) < 2: continue
        # Skip rows that look like the footer
        if 'Actualizado' in n: continue
        projects.append({
            'nombre': n,
            'dept':   str(row[1] or '').strip(),
            'resp':   str(row[2] or '—').strip(),
            'estado': str(row[3] or '—').strip(),
            'hito':   str(row[4] or '—').strip(),
            'fecha':  str(row[5] or '—').strip(),
            'bloqueador':   str(row[6] or '—').strip(),
            'constructora': str(row[7] or '—').strip(),
            'fase':    str(row[8] or '—').strip(),
            'atencion':str(row[9] or '—').strip(),
            'nivel':   str(row[10] or '—').strip(),
            'obs':     str(row[11] or '').strip() if len(row) > 11 else '',
            'tl': {}
        })
    return projects

# ── PLANNING (Gantt) ──────────────────────────────────────────────────────────
# Estructura Excel: row1=estudio, row2=meses, row3=cabecera (Nº|PROYECTO|...|1SEP|8SEP|...)
#                  row4+=datos
def extract_planning(sheet_name):
    if not sheet_name: return {}
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(min_row=1, max_row=ws.max_row,
                              max_col=ws.max_column, values_only=True))
    week_cols = {}   # col_index (0-based) → week_index
    header_idx = None

    # Buscar fila de fechas (tiene dígitos en columnas >4) y fila de cabecera (col1=='PROYECTO')
    dates_idx = None
    for i, row in enumerate(rows):
        if len(row) > 1 and str(row[1] or '').strip() == 'PROYECTO':
            header_idx = i
            # Las semanas: buscar en esta fila o en la anterior la fila con fechas
            src_row = row
            if dates_idx is not None:
                src_row = rows[dates_idx]
            week_counter = 0
            for j in range(5, len(src_row)):
                c = src_row[j]
                c_str = str(c or '').strip()
                if c_str and any(ch.isdigit() for ch in c_str):
                    week_cols[j] = week_counter
                    if week_counter >= len(WEEK_LABELS):
                        WEEK_LABELS.append(c_str)
                    week_counter += 1
            break
        # Detectar fila de fechas (ej: '28 SEP', '5 OCT'...)
        date_count = sum(1 for c in row if c and any(ch.isdigit() for ch in str(c or '')) and any(ch.isalpha() for ch in str(c or '')))
        if date_count >= 3:
            dates_idx = i

    if not week_cols or header_idx is None:
        print(f"  ⚠ No se encontró cabecera en {sheet_name}")
        return {}

    print(f"  {sheet_name}: cabecera en fila {header_idx+1}, {len(week_cols)} semanas")

    tl = {}
    for row in rows[header_idx + 1:]:
        if not row or len(row) < 2: continue
        n = row[1]
        if not n or not isinstance(n, str): continue
        n = n.strip()
        if len(n) < 2 or n.startswith('▸') or n.startswith('──'): continue
        if n.upper() in ('VACACIONES', 'PROYECTO'): continue

        phases = {}
        for col, idx in week_cols.items():
            if col < len(row) and row[col] and str(row[col]).strip() not in {'None','','—'}:
                phases[idx] = str(row[col]).strip()
        if phases:
            tl[n.upper()] = phases
    return tl

# ── Extraer timelines ─────────────────────────────────────────────────────────
# Intentar hoja PLANNING unificada primero
planning_sheet = find_sheet('PLANNING')
all_tl = extract_planning(planning_sheet) if planning_sheet else {}

# Hojas separadas por departamento (estructura actual del Excel)
if not all_tl:
    tl_viv  = extract_planning(find_sheet('VIVIENDA'))
    tl_hot  = extract_planning(find_sheet('HOTELES'))
    tl_rest = extract_planning(find_sheet('RESTAURANTES'))
    all_tl  = {**tl_viv, **tl_hot, **tl_rest}
    print(f"Timelines: VIV={len(tl_viv)} HOT={len(tl_hot)} REST={len(tl_rest)} TOTAL={len(all_tl)}")
else:
    print(f"Timelines (PLANNING): {len(all_tl)} proyectos")

MASTER = extract_master()

# Cruzar timelines con MASTER
for p in MASTER:
    key = p['nombre'].upper()
    for k, phases in all_tl.items():
        if k == key or k in key or key in k:
            p['tl'] = phases; break

print(f"Master: {len(MASTER)} proyectos, con timeline: {sum(1 for p in MASTER if p['tl'])}")

# ── ALERTAS derivadas del MASTER ─────────────────────────────────────────────
ALERTAS_JSON = [
    {
        'proj':  p['nombre'],
        'dept':  p['dept'],
        'resp':  p['resp'],
        'text':  p['hito'] + (' — ' + p['bloqueador']
                 if p['bloqueador'] not in ('—', '', 'None') else ''),
        'fecha': p['fecha'],
        'risk':  'CRITICO' if p['nivel'] == 'ATENCIÓN MÁXIMA' else 'ALTO'
    }
    for p in MASTER
    if p['nivel'] in ('ATENCIÓN MÁXIMA', 'ATENCIÓN ALTA')
]

# ── RESUMEN ALEJANDRA — generado desde MASTER ─────────────────────────────────
# Intentar leer de hoja si existe; si no, generar desde MASTER
ALE_ALERTAS, ALE_HITOS, ALE_MONTAJES, ALE_PRESENCIA, ALE_PROXIMAS = [], [], [], [], []
ale_sheet = find_sheet('Resumen','RESUMEN')
if ale_sheet:
    try:
        ws_ale = wb[ale_sheet]
        rows_ale = list(ws_ale.iter_rows(values_only=True))
        section = None
        for row in rows_ale:
            if not any(c for c in row): continue
            first = str(row[0] or '').strip()
            if 'ALERTAS' in first.upper(): section = 'alertas'; continue
            if 'HITOS' in first.upper(): section = 'hitos'; continue
            if 'MONTAJES' in first.upper(): section = 'montajes'; continue
            if 'PRESENCIA' in first.upper(): section = 'presencia'; continue
            if 'PRÓXIMAS' in first.upper() or 'PROXIMAS' in first.upper():
                section = 'proximas'; continue
            if first in ('NIVEL','CUÁNDO','FECHAS','FECHA','SEMANA'): continue
            if 'Alejandra Pombo' in first or first.startswith('Solo se'): continue
            if section == 'alertas' and row[0] and row[1]:
                nivel = str(row[0]).strip()
                if nivel in ('ATENCIÓN MÁXIMA','ATENCIÓN ALTA'):
                    ALE_ALERTAS.append({'nivel':nivel,'proj':str(row[1]).strip(),
                        'resp':str(row[2] or '').strip(),'text':str(row[3] or '').strip(),
                        'risk':'CRITICO' if nivel=='ATENCIÓN MÁXIMA' else 'ALTO'})
            elif section == 'hitos' and row[0] and row[1]:
                ALE_HITOS.append({'when':str(row[0]).strip(),'proj':str(row[1]).strip(),
                    'quien':str(row[2] or '').strip(),'text':str(row[3] or '').strip()})
            elif section == 'montajes' and row[0] and row[1]:
                ALE_MONTAJES.append({'fechas':str(row[0]).strip(),'proj':str(row[1]).strip(),
                    'equipo':str(row[2] or '').strip(),'notas':str(row[3] or '').strip()})
            elif section == 'presencia' and row[0] and row[1]:
                ALE_PRESENCIA.append({'fecha':str(row[0]).strip(),'texto':str(row[1]).strip()})
            elif section == 'proximas' and row[0] and row[1]:
                ALE_PROXIMAS.append({'sem':str(row[0]).strip(),'items':[str(row[1]).strip()]})
    except Exception as e:
        print(f"  ⚠ Error leyendo Resumen Alejandra: {e}")

# Si no hay hoja, derivar alertas del MASTER
if not ALE_ALERTAS:
    ALE_ALERTAS = [{'nivel':p['nivel'],'proj':p['nombre'],'resp':p['resp'],
        'text':p['hito'],'risk':'CRITICO' if p['nivel']=='ATENCIÓN MÁXIMA' else 'ALTO'}
        for p in MASTER if p['nivel'] in ('ATENCIÓN MÁXIMA','ATENCIÓN ALTA')]

print(f"Resumen Alejandra: {len(ALE_ALERTAS)} alertas, {len(ALE_HITOS)} hitos")

# ── FOCO POR PERSONA ─────────────────────────────────────────────────────────
NOMBRE_MAP = {
    'PM':'javi','Sofía':'sofia','Naiara':'naiara','Paula':'paula',
    'Sara':'sara','Olatz':'olatz','Marta':'marta','Andrea':'andrea',
    'Cristina':'cristina','Nela':'nela','Jesús':'jesus','Alejandra — CEO':'ale'
}
NOMBRE_DISPLAY = {
    'javi':'Javi','sofia':'Sofía','naiara':'Naiara','paula':'Paula','sara':'Sara',
    'olatz':'Olatz','marta':'Marta','andrea':'Andrea','cristina':'Cristina',
    'nela':'Nela','jesus':'Jesús','ale':'Alejandra'
}
PERSON_ORDER = ['javi','ale']
DEPT_SECTIONS = {'VIVIENDA':[],'RESTAURANTES':[],'HOTELES':[]}
PROJS_PERSONA, DEPT_PERSONA, NOMBRE_PERSONA, FOCO_SEMANA = {}, {}, {}, {}

foco_sheet = find_sheet('FOCO','PERSONA')
if foco_sheet:
    try:
        ws_foco = wb[foco_sheet]
        current_dept = None
        for row in ws_foco.iter_rows(min_row=2, values_only=True):
            if not row[0]: continue
            nombre_excel = str(row[0]).strip()
            if nombre_excel.startswith('──'):
                if 'VIVIENDA' in nombre_excel.upper(): current_dept = 'VIVIENDA'
                elif 'RESTAURANTE' in nombre_excel.upper(): current_dept = 'RESTAURANTES'
                elif 'HOTEL' in nombre_excel.upper(): current_dept = 'HOTELES'
                continue
            pid = NOMBRE_MAP.get(nombre_excel)
            if not pid: continue
            dept_raw = str(row[1] or '').strip()
            if 'VIVIENDA' in dept_raw: dept = 'Vivienda'
            elif 'HOTEL' in dept_raw: dept = 'Hoteles'
            elif 'RESTAURANTE' in dept_raw: dept = 'Restaurantes'
            else: dept = 'todos'
            projs = [p.strip().upper() for p in str(row[2] or '').replace('·','|').split('|')
                     if p.strip() and len(p.strip()) > 2]
            foco_items = [f.strip() for f in str(row[3] or '').split('·')
                          if f.strip() and len(f.strip()) > 4]
            NOMBRE_PERSONA[pid] = NOMBRE_DISPLAY.get(pid, nombre_excel)
            DEPT_PERSONA[pid] = dept
            PROJS_PERSONA[pid] = projs[:8]
            FOCO_SEMANA[pid] = foco_items[:6]
            if pid not in ('javi','ale'):
                target = current_dept or ('VIVIENDA' if dept=='Vivienda' else
                          'RESTAURANTES' if dept=='Restaurantes' else 'HOTELES')
                if target in DEPT_SECTIONS:
                    DEPT_SECTIONS[target].append(pid)
        for dept_pids in DEPT_SECTIONS.values():
            PERSON_ORDER.extend(dept_pids)
    except Exception as e:
        print(f"  ⚠ Error leyendo Foco por persona: {e}")

# Si no hay hoja de foco, derivar personas del MASTER
if not NOMBRE_PERSONA:
    # Generar foco básico desde responsables en MASTER
    seen_pid = set()
    for p in MASTER:
        for resp_raw in str(p.get('resp','')).replace('/',' ').replace('+',' ').split():
            pid = NOMBRE_MAP.get(resp_raw.strip())
            if pid and pid not in seen_pid and pid not in ('javi','ale'):
                seen_pid.add(pid)
                NOMBRE_PERSONA[pid] = NOMBRE_DISPLAY.get(pid, resp_raw)
                DEPT_PERSONA[pid] = p.get('dept','').capitalize()
                PROJS_PERSONA[pid] = []
                FOCO_SEMANA[pid] = []
                dept = p.get('dept','').upper()
                if dept in DEPT_SECTIONS:
                    DEPT_SECTIONS[dept].append(pid)
    for dept_pids in DEPT_SECTIONS.values():
        PERSON_ORDER.extend(dept_pids)

print(f"Personas: {PERSON_ORDER}")

# ── RENDERS ───────────────────────────────────────────────────────────────────
RENDERS = []
renders_sheet = find_sheet('Render','render','RENDER')
if renders_sheet:
    try:
        ws_r = wb[renders_sheet]
        header = False
        for row in ws_r.iter_rows(values_only=True):
            if not any(c for c in row): continue
            first = str(row[0] or '').strip()
            if first == 'PRIO': header = True; continue
            if not header: continue
            if not row[0] or str(row[0]).strip().startswith(('▸','──')): continue
            prio_raw = str(row[0]).strip()
            prio = 'URGENTE' if '🔴' in prio_raw else 'MEDIO' if '🟠' in prio_raw else 'BAJO'
            proj = str(row[1] or '').strip()
            if not proj or len(proj) < 2: continue
            RENDERS.append({
                'prio':prio,'proj':proj,'dept':str(row[2] or '').strip(),
                'resp':str(row[3] or '').strip(),'renderista':str(row[4] or 'Challan').strip(),
                'fase':str(row[5] or '').strip(),'estado':str(row[6] or '').strip(),
                'comprometida':str(row[8] or '').strip() if len(row)>8 else '',
                'realista':str(row[9] or '').strip() if len(row)>9 else '',
                'next':str(row[10] or '').strip() if len(row)>10 else '',
                'riesgo':'CRITICO' if prio=='URGENTE' else 'MEDIO'
            })
    except Exception as e:
        print(f"  ⚠ Error leyendo Renders: {e}")

RENDERS_FLUJO = [
    {'fase':'F1','titulo':'Volumetría y capturas','desc':'Planos + 3D + vistas marcadas. ~1 semana desde doc completa.'},
    {'fase':'F2','titulo':'Materialidad y acabados','desc':'Toda la info de acabados y mobiliario. 2-3 días.'},
    {'fase':'F3','titulo':'Render final','desc':'TODAS las correcciones cerradas ANTES de renderizar.'},
]
RENDERS_REGLAS = [
    'Máx. 2-3 proyectos activos simultáneos por renderista.',
    'Nunca activar sin documentación 100% completa.',
    'PM es el filtro — nadie pasa trabajo sin visto bueno del PM.',
]

MONTAJES = ALE_MONTAJES if ALE_MONTAJES else []
AGENDA = [{'when':a['when'],'text':f"{a['proj']} — {a['text']}"} for a in ALE_HITOS[:8]]
VAC = {}

# ── ID ESTABLE: mismo algoritmo para las tres fuentes ─────────────────────────
import re as _re
def make_id(nombre):
    """ID estable desde nombre: quitar número inicial, limpiar, snake_case.
    Ej: '217 PASEO LAGOS 132' → 'paseo_lagos_132'
        'PASEO LAGOS 132'     → 'paseo_lagos_132'
    """
    n = str(nombre or '').strip()
    n = _re.sub(r'^\d+\s*', '', n)           # quitar número inicial
    n = n.upper()
    for a, b in [('Á','A'),('É','E'),('Í','I'),('Ó','O'),('Ú','U'),('Ñ','N'),
                 ('À','A'),('È','E'),('Ì','I'),('Ò','O'),('Ù','U')]:
        n = n.replace(a, b)
    n = _re.sub(r'[^\w\s]', '', n)
    n = _re.sub(r'\s+', '_', n.strip())
    return n.lower()[:40]

# Asignar IDs al MASTER
for p in MASTER:
    p['id'] = make_id(p['nombre'])

# ── LEER GLOBAL (Master_Global.xlsx en el repo) ────────────────────────────────
# Cols: PROYECTO | RESPONSABLE | FASE REAL | ACTIVIDAD ACTUAL | FECHA OBJETIVO |
#       FIN OBRA | MONTAJE | ENTREGA | DECO CERRADA | PRESU. DECO | PEDIDOS |
#       SITUACIÓN/BLOQUEADOR | ACCIÓN CONCRETA | CUÁNDO
GLOBAL_EXCEL = os.path.join(BASE, 'Master_Global.xlsx')
_global_raw = {}
if os.path.exists(GLOBAL_EXCEL):
    wb_g = openpyxl.load_workbook(GLOBAL_EXCEL, data_only=True)
    ws_g = wb_g[wb_g.sheetnames[0]]
    rows_g = list(ws_g.iter_rows(min_row=1, max_row=ws_g.max_row, max_col=15, values_only=True))
    header_g = False
    for row in rows_g:
        if str(row[0] or '').strip() == 'PROYECTO':
            header_g = True; continue
        if not header_g: continue
        n = str(row[0] or '').strip()
        if not n or len(n) < 3: continue
        if n.startswith(('▸','🔴','🟠','🟡','  ')): continue
        gid = make_id(n)
        _global_raw[gid] = {
            'id':                  gid,
            'nombre_original':     n,
            'fase_real':           str(row[2]  or '—').strip(),
            'actividad_actual':    str(row[3]  or '—').strip(),
            'atencion':            str(row[1]  or '').strip(),
            'fecha_hito':          str(row[4]  or '—').strip(),
            'fin_obra':            str(row[5]  or '—').strip(),
            'montaje':             str(row[6]  or '—').strip(),
            'entrega':             str(row[7]  or '—').strip(),
            'deco_cerrada':        str(row[8]  or '—').strip(),
            'presupuesto_deco_aceptado': str(row[9] or '—').strip(),
            'pedidos_confirmados': str(row[10] or '—').strip(),
            'bloqueador':          str(row[11] or '').strip(),
            'accion_concreta':     str(row[12] or '').strip(),
            'cuando':              str(row[13] or '').strip(),
        }
    print(f"Global (Master_Global.xlsx): {len(_global_raw)} proyectos")
else:
    print("⚠ Master_Global.xlsx no encontrado — GLOBAL vacío")

# ── LEER PLANNING (PLANNING_POMBO.xlsx en el repo) ────────────────────────────
# Estructura: row1=estudio, row2=meses, row3=fechas, row4=cabecera, row5+=datos
# Cols: DPTO | PROYECTO | RESPONSABLE | FASE | PRÓXIMO HITO | sem1 | sem2 | ...
PLANNING_EXCEL = os.path.join(BASE, 'PLANNING_POMBO.xlsx')
_planning_raw  = {}   # id → {fases: {week_idx: label}}
_planning_cols = {}   # col_idx → week_idx
_week_labels_p = []
if os.path.exists(PLANNING_EXCEL):
    wb_p = openpyxl.load_workbook(PLANNING_EXCEL, data_only=True)
    ws_p = wb_p[wb_p.sheetnames[0]]
    rows_p = list(ws_p.iter_rows(min_row=1, max_row=ws_p.max_row,
                                  max_col=ws_p.max_column, values_only=True))
    dates_idx_p = None
    header_idx_p = None
    for i, row in enumerate(rows_p):
        if len(row) > 1 and str(row[1] or '').strip() == 'PROYECTO':
            header_idx_p = i
            src = rows_p[dates_idx_p] if dates_idx_p is not None else row
            wc = 0
            for j in range(5, len(src)):
                c = str(src[j] or '').strip()
                if c and any(ch.isdigit() for ch in c):
                    _planning_cols[j] = wc
                    _week_labels_p.append(c)
                    wc += 1
            break
        date_count = sum(1 for c in row
                         if c and any(ch.isdigit() for ch in str(c))
                         and any(ch.isalpha() for ch in str(c)))
        if date_count >= 3:
            dates_idx_p = i

    if header_idx_p is not None:
        for row in rows_p[header_idx_p + 1:]:
            if not row or len(row) < 2: continue
            n = str(row[1] or '').strip()
            if not n or len(n) < 2 or n.startswith('▸'): continue
            if n.upper() in ('PROYECTO', 'VACACIONES'): continue
            pid = make_id(n)
            fases = {}
            for col, idx in _planning_cols.items():
                if col < len(row) and row[col] and str(row[col]).strip() not in {'','—','None'}:
                    fases[idx] = str(row[col]).strip()
            if fases:
                _planning_raw[pid] = {
                    'id':    pid,
                    'dpto':  str(row[0] or '').strip(),
                    'resp':  str(row[2] or '').strip(),
                    'fase':  str(row[3] or '').strip(),
                    'hito':  str(row[4] or '').strip(),
                    'fases': fases,
                }
    print(f"Planning (PLANNING_POMBO.xlsx): {len(_planning_raw)} proyectos, {len(_week_labels_p)} semanas")
    if _week_labels_p:
        WEEK_LABELS = _week_labels_p
else:
    print("⚠ PLANNING_POMBO.xlsx no encontrado — usando PLANNING del master")

# ── FUSIONAR LAS TRES FUENTES ──────────────────────────────────────────────────
# Base: proyectos del MASTER (identidad + estado)
# Completar con proyectos del GLOBAL que no estén en el MASTER
# Completar con proyectos del PLANNING que no estén en ninguno de los dos

_master_index = {p['id']: p for p in MASTER}

# Proyectos en GLOBAL pero no en MASTER → añadir stub desde GLOBAL
for gid, g in _global_raw.items():
    if gid not in _master_index:
        # Derivar nombre legible desde la clave del global (el gid ya es limpio)
        # Buscar el nombre original en _global_raw (necesitamos el nombre original)
        # Lo recuperamos directamente del raw ya que g no tiene 'nombre' aún
        # Re-leer del Excel no es viable aquí — usamos el id como proxy
        _master_index[gid] = {
            'id': gid,
            'nombre': g.get('nombre_original', gid.replace('_',' ').upper()),
            'dept':   '',
            'resp':   '',
            'estado': '',
            'hito':   g.get('actividad_actual', '—'),
            'fecha':  g.get('fecha_hito', '—'),
            'bloqueador': g.get('bloqueador', ''),
            'constructora': '—',
            'fase':   g.get('fase_real', '—'),
            'atencion': '',
            'nivel':  '',
            'obs':    g.get('accion_concreta', ''),
            'tl': {},
        }

# Proyectos en PLANNING pero no en ninguno de los dos
for pid, pr in _planning_raw.items():
    if pid not in _master_index:
        _master_index[pid] = {
            'id':    pid,
            'nombre': pid.replace('_',' ').upper(),
            'dept':   pr.get('dpto', ''),
            'resp':   pr.get('resp', ''),
            'estado': '',
            'hito':   pr.get('hito', '—'),
            'fecha':  '—',
            'bloqueador': '',
            'constructora': '—',
            'fase':   pr.get('fase', '—'),
            'atencion': '',
            'nivel':  '',
            'obs':    '',
            'tl': {},
        }

# Lista unificada (MASTER primero para mantener orden original)
_all_projects = list(MASTER) + [
    p for pid, p in _master_index.items() if pid not in {m['id'] for m in MASTER}
]

# ── MASTER_DATA ────────────────────────────────────────────────────────────────
MASTER_DATA = []
for p in _all_projects:
    pid = p['id']
    g   = _global_raw.get(pid, {})
    MASTER_DATA.append({
        'id':           pid,
        'nombre':       p['nombre'],
        'dpto':         p['dept'],
        'equipo':       [r.strip() for r in
                         str(p.get('resp','')).replace('/',' / ').replace('+',' / ').split('/')
                         if r.strip() and len(r.strip()) > 1],
        'estado':       p['estado'],
        'hito':         p['hito'],
        'fecha':        p['fecha'],
        'bloqueador':   p['bloqueador'],
        'constructora': p['constructora'],
        'fase':         p['fase'],
        'atencion':     p['atencion'],
        'nivel':        p['nivel'],
        'obs':          p['obs'],
        # Campos de GLOBAL que el modal accede en proj. directamente
        'fin_obra':     g.get('fin_obra', '—'),
        'montaje':      g.get('montaje', '—'),
        'entrega':      g.get('entrega', '—'),
        'deco_cerrada': g.get('deco_cerrada', '—'),
        'presupuesto_deco_aceptado': g.get('presupuesto_deco_aceptado', '—'),
        'pedidos_confirmados': g.get('pedidos_confirmados', '—'),
    })

# ── GLOBAL_DATA (campos que app.js accede vía _g = globalOf(id)) ──────────────
GLOBAL_DATA = []
for p in _all_projects:
    pid = p['id']
    g   = _global_raw.get(pid, {})
    GLOBAL_DATA.append({
        'id':              pid,
        'atencion':        p['atencion'],
        'proximo_hito':    g.get('actividad_actual', p['hito']),
        'fecha_hito':      g.get('fecha_hito', p['fecha']),
        'bloqueador':      g.get('bloqueador', p['bloqueador']),
        'obs':             g.get('accion_concreta', p['obs']),
        'cuando':          g.get('cuando', ''),
        'fase_real':       g.get('fase_real', p['fase']),
        'fin_obra':        g.get('fin_obra', '—'),
        'montaje':         g.get('montaje', '—'),
        'entrega':         g.get('entrega', '—'),
    })

# ── PLANNING_DATA ──────────────────────────────────────────────────────────────
# app.js espera: proyectos[].timeline = [{semana: "6 OCT", actividades:[{texto:"OBRA"}]}, ...]
# Los índices numéricos en _planning_raw.fases se convierten a etiquetas de semana.

def fases_to_timeline(fases_dict, week_labels):
    """Convierte {week_idx: label} → [{semana: week_label, actividades:[{texto:label}]}]"""
    tl = []
    for idx, label in fases_dict.items():
        try:
            i = int(idx)
            if 0 <= i < len(week_labels):
                tl.append({'semana': week_labels[i], 'actividades': [{'texto': str(label)}]})
        except (ValueError, TypeError):
            pass
    return tl

planning_proyectos = []
# Primero del PLANNING_POMBO
for pid, pr in _planning_raw.items():
    tl = fases_to_timeline(pr['fases'], WEEK_LABELS)
    if tl:
        planning_proyectos.append({'id': pid, 'timeline': tl})
# Completar con los del MASTER que no estén ya (tl es {nombre_semana: label})
ids_en_planning = {pr['id'] for pr in planning_proyectos}
for p in MASTER:
    if p['id'] not in ids_en_planning and p.get('tl'):
        # tl del MASTER viene del extract_planning, que ya usa nombre de semana como clave
        tl = [{'semana': sem, 'actividades': [{'texto': str(lbl)}]}
              for sem, lbl in p['tl'].items() if sem and lbl]
        if tl:
            planning_proyectos.append({'id': p['id'], 'timeline': tl})

# Recalcular TODAY_WEEK con las semanas del planning
if _week_labels_p:
    import datetime as _dt
    def _parse_week(label):
        parts = label.strip().split()
        if len(parts) == 2:
            meses = {'ENE':1,'FEB':2,'MAR':3,'ABR':4,'MAY':5,'JUN':6,
                     'JUL':7,'AGO':8,'SEP':9,'OCT':10,'NOV':11,'DIC':12}
            m = meses.get(parts[1].upper()[:3])
            if m:
                try: return _dt.date(2026, m, int(parts[0]))
                except: pass
        return None
    fechas = [(_parse_week(l), i) for i, l in enumerate(_week_labels_p)]
    fechas = [(f, i) for f, i in fechas if f]
    if fechas:
        hoy_date = _dt.date.today()
        pasadas = [(f, i) for f, i in fechas if f <= hoy_date]
        TODAY_WEEK = pasadas[-1][1] if pasadas else 0

PLANNING_DATA = {
    'semanas':   WEEK_LABELS,
    'meses':     MONTHS,
    'hoy':       TODAY_WEEK,
    'proyectos': planning_proyectos,
}

# hoy_semana debe ser el LABEL de la semana actual (string), no el índice numérico.
# app.js hace sems.indexOf(hoySemana()) — necesita el mismo string que está en WEEK_LABELS.
HOY_SEMANA_LABEL = WEEK_LABELS[TODAY_WEEK] if 0 <= TODAY_WEEK < len(WEEK_LABELS) else ''

META = {
    'updated':    hoy.strftime('%d %b %Y'),
    'hoy_semana': HOY_SEMANA_LABEL,
}

# ── GENERAR DATA JS ───────────────────────────────────────────────────────────
DATA_JS = f"""
const MASTER_DATA = {json.dumps(MASTER_DATA, ensure_ascii=False)};
const GLOBAL_DATA = {json.dumps(GLOBAL_DATA, ensure_ascii=False)};
const PLANNING_DATA = {json.dumps(PLANNING_DATA, ensure_ascii=False)};
const META = {json.dumps(META, ensure_ascii=False)};
const ALERTAS = {json.dumps(ALERTAS_JSON, ensure_ascii=False)};
const AGENDA = {json.dumps(AGENDA, ensure_ascii=False)};
const MONTAJES = {json.dumps(MONTAJES, ensure_ascii=False)};
const ALE_ALERTAS = {json.dumps(ALE_ALERTAS, ensure_ascii=False)};
const ALE_HITOS = {json.dumps(ALE_HITOS, ensure_ascii=False)};
const ALE_MONTAJES = {json.dumps(ALE_MONTAJES, ensure_ascii=False)};
const ALE_PRESENCIA = {json.dumps(ALE_PRESENCIA, ensure_ascii=False)};
const ALE_PROXIMAS = {json.dumps(ALE_PROXIMAS, ensure_ascii=False)};
const RENDERS = {json.dumps(RENDERS, ensure_ascii=False)};
const RENDERS_FLUJO = {json.dumps(RENDERS_FLUJO, ensure_ascii=False)};
const RENDERS_REGLAS = {json.dumps(RENDERS_REGLAS, ensure_ascii=False)};
const RENDERS_VAC = '';
const FOCO_SEMANA = {json.dumps(FOCO_SEMANA, ensure_ascii=False)};
const PROJS_PERSONA = {json.dumps(PROJS_PERSONA, ensure_ascii=False)};
const DEPT_PERSONA = {json.dumps(DEPT_PERSONA, ensure_ascii=False)};
const NOMBRE_PERSONA = {json.dumps(NOMBRE_PERSONA, ensure_ascii=False)};
const VAC = {json.dumps(VAC, ensure_ascii=False)};
const DEPT_SECTIONS = {json.dumps(DEPT_SECTIONS, ensure_ascii=False)};
const PERSON_ORDER = {json.dumps(PERSON_ORDER)};
"""

# ── CONSTRUIR HTML ────────────────────────────────────────────────────────────
import re

def escape_script_close(s):
    return s.replace('</script', '<\\/script')

head_html = open(os.path.join(BASE, 'head.html'), encoding='utf-8').read()
app_js    = open(os.path.join(BASE, 'app.js'),   encoding='utf-8').read()

html_out = (head_html +
    '<script>\n' + escape_script_close(DATA_JS) + '\n</script>\n' +
    '<script>\n' + app_js + '\n</script>\n' +
    '</body>\n</html>')

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html_out)

print(f"\n✅ App generada: {OUT}")
print(f"   Proyectos: {len(MASTER)} | Alertas: {len(ALERTAS_JSON)} | Con timeline: {sum(1 for p in MASTER if p['tl'])}")
