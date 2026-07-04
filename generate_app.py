#!/usr/bin/env python3
"""
APDS PM Estudio — Generador de app v2
Lee PM_ESTUDIO_MASTER_COMPLETO.xlsx y genera docs/index.html
Requiere: app.js y head.html en el mismo directorio
"""
import openpyxl, json, os
from datetime import date

BASE = os.path.dirname(os.path.abspath(__file__))
EXCEL = os.path.join(BASE, 'PM_ESTUDIO_MASTER_COMPLETO.xlsx')
OUT   = os.path.join(BASE, 'docs', 'index.html')
APP_JS_FILE = os.path.join(BASE, 'app.js')

wb = openpyxl.load_workbook(EXCEL, data_only=True)
print("Hojas:", wb.sheetnames)

hoy = date.today()
sem_inicio = date(2026, 6, 17)
TODAY_WEEK = max(0, min((hoy - sem_inicio).days // 7, 15))
WEEK_LABELS = ['17-19J','22-26J','29J-3Jl','6-10Jl','13-17Jl','20-24Jl','27-31Jl',
               '3-7A','10-14A','17-21A','24-28A','31A-4S','7-11S','14-18S','21-25S','28-2O']
MONTHS = [["JUN",0,0],["JUL",1,5],["AGO",6,9],["SEP",10,13],["OCT",14,15]]

def find_sheet(*keywords):
    for s in wb.sheetnames:
        if any(k.upper() in s.upper() for k in keywords):
            return s
    return None

# ── MASTER GLOBAL ──────────────────────────────────────────────────────────────
def extract_master():
    ws = wb[find_sheet('MASTER','GLOBAL')]
    projects, header = [], False
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=ws.max_column, values_only=True):
        if not any(c for c in row): continue
        if str(row[0] or '').strip() == 'PROYECTO':
            header = True; continue
        if not header or not row[0] or not isinstance(row[0], str): continue
        n = str(row[0]).strip()
        if n.startswith('▸') or n.startswith('—') or n.startswith('──') or len(n) < 2: continue
        projects.append({
            'nombre': n, 'dept': str(row[1] or '').strip(),
            'resp': str(row[2] or '—').strip(), 'estado': str(row[3] or '—').strip(),
            'hito': str(row[4] or '—').strip(), 'fecha': str(row[5] or '—').strip(),
            'bloqueador': str(row[6] or '—').strip(), 'constructora': str(row[7] or '—').strip(),
            'fase': str(row[8] or '—').strip(), 'atencion': str(row[9] or '—').strip(),
            'nivel': str(row[10] or '—').strip(),
            'obs': str(row[11] or '').strip() if len(row) > 11 else '',
            'tl': {}
        })
    return projects

def extract_planning(sheet_name):
    if not sheet_name: return {}
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=ws.max_column, values_only=True))
    week_cols, header_idx = {}, None
    for i, row in enumerate(rows):
        if str(row[0] or '').strip() == 'PROYECTO':
            header_idx = i
            for j in range(2, len(row)):
                c = row[j]
                if c and isinstance(c, str) and any(ch.isdigit() for ch in c):
                    week_cols[j] = j - 2
            break
    if not week_cols or header_idx is None: return {}
    tl = {}
    for row in rows[header_idx + 1:]:
        n = row[0]
        if not n or not isinstance(n, str): continue
        n = n.strip()
        if len(n) < 2 or n.startswith('▸') or n.startswith('──'): continue
        phases = {}
        for col, idx in week_cols.items():
            if col < len(row) and row[col] and str(row[col]).strip() not in {'None',''}:
                phases[idx] = str(row[col]).strip()
        if phases:
            tl[n.upper()] = phases
    return tl

tl_viv  = extract_planning(find_sheet('Vivienda','VIVIENDA'))
tl_hot  = extract_planning(find_sheet('Hotel','HOTEL'))
tl_rest = extract_planning(find_sheet('Restaurante','REST'))
all_tl  = {**tl_viv, **tl_hot, **tl_rest}

MASTER = extract_master()
for p in MASTER:
    key = p['nombre'].upper()
    for k, phases in all_tl.items():
        if k == key or k in key or key in k:
            p['tl'] = phases; break

print(f"Master: {len(MASTER)} proyectos, con timeline: {sum(1 for p in MASTER if p['tl'])}")

# ── RESUMEN ALEJANDRA ──────────────────────────────────────────────────────────
ws_ale = wb[find_sheet('Resumen','RESUMEN')]
rows_ale = list(ws_ale.iter_rows(min_row=1, max_row=ws_ale.max_row, max_col=ws_ale.max_column, values_only=True))
ALE_ALERTAS, ALE_HITOS, ALE_MONTAJES, ALE_PRESENCIA, ALE_PROXIMAS = [], [], [], [], []
section = None
for row in rows_ale:
    if not any(c for c in row): continue
    first = str(row[0] or '').strip()
    if 'ALERTAS' in first.upper(): section = 'alertas'; continue
    if 'HITOS' in first.upper(): section = 'hitos'; continue
    if 'MONTAJES' in first.upper(): section = 'montajes'; continue
    if 'PRESENCIA' in first.upper(): section = 'presencia'; continue
    if 'PRÓXIMAS' in first.upper() or 'PROXIMAS' in first.upper(): section = 'proximas'; continue
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

print(f"Resumen Alejandra: {len(ALE_ALERTAS)} alertas, {len(ALE_HITOS)} hitos")

# ── FOCO POR PERSONA ───────────────────────────────────────────────────────────
ws_foco = wb[find_sheet('FOCO','PERSONA')]
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
current_dept = None
for row in ws_foco.iter_rows(min_row=2, max_row=ws_foco.max_row, max_col=ws_foco.max_column, values_only=True):
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
    if 'VIVIENDA' in dept_raw and 'HOT' not in dept_raw and 'RES' not in dept_raw: dept = 'Vivienda'
    elif 'HOTEL' in dept_raw: dept = 'Hoteles'
    elif 'RESTAURANTE' in dept_raw: dept = 'Restaurantes'
    else: dept = 'todos'
    projs = [p.strip().upper() for p in str(row[2] or '').replace('·','|').split('|') if p.strip() and len(p.strip()) > 2]
    foco_items = [f.strip() for f in str(row[3] or '').split('·') if f.strip() and len(f.strip()) > 4]
    NOMBRE_PERSONA[pid] = NOMBRE_DISPLAY.get(pid, nombre_excel)
    DEPT_PERSONA[pid] = dept
    PROJS_PERSONA[pid] = projs[:8]
    FOCO_SEMANA[pid] = foco_items[:6]
    if pid not in ('javi','ale'):
        if current_dept and current_dept in DEPT_SECTIONS:
            DEPT_SECTIONS[current_dept].append(pid)
        elif dept == 'Vivienda': DEPT_SECTIONS['VIVIENDA'].append(pid)
        elif dept == 'Restaurantes': DEPT_SECTIONS['RESTAURANTES'].append(pid)
        elif dept == 'Hoteles': DEPT_SECTIONS['HOTELES'].append(pid)
for dept_pids in DEPT_SECTIONS.values():
    PERSON_ORDER.extend(dept_pids)
print(f"Personas: {PERSON_ORDER}")

# ── RENDERS ────────────────────────────────────────────────────────────────────
def extract_renders():
    sheet = find_sheet('Render','render')
    if not sheet: return []
    ws = wb[sheet]
    renders, header = [], False
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=ws.max_column, values_only=True):
        if not any(c for c in row): continue
        first = str(row[0] or '').strip()
        if first == 'PRIO': header = True; continue
        if not header: continue
        if not row[0] or not isinstance(row[0], str): continue
        if str(row[0]).strip().startswith(('▸','──')): continue
        prio_raw = str(row[0]).strip()
        prio = 'URGENTE' if '🔴' in prio_raw else 'MEDIO' if '🟠' in prio_raw else 'BAJO'
        proj = str(row[1] or '').strip()
        if not proj or len(proj) < 2: continue
        renders.append({
            'prio':prio,'proj':proj,'dept':str(row[2] or '').strip(),
            'resp':str(row[3] or '').strip(),'renderista':str(row[4] or 'Challan').strip(),
            'fase':str(row[5] or '').strip(),'estado':str(row[6] or '').strip(),
            'comprometida':str(row[8] or '').strip(),'realista':str(row[9] or '').strip(),
            'next':str(row[10] or '').strip(),
            'riesgo':'CRITICO' if prio=='URGENTE' else 'MEDIO'
        })
    return renders

RENDERS = extract_renders()
ALERTAS_JSON = [{'proj':p['nombre'],'dept':p['dept'],'resp':p['resp'],
    'text':p['hito']+(' — '+p['bloqueador'] if p['bloqueador'] not in ('—','') else ''),
    'fecha':p['fecha'],'risk':'CRITICO' if p['nivel']=='ATENCIÓN MÁXIMA' else 'ALTO'}
    for p in MASTER if p['nivel'] in ('ATENCIÓN MÁXIMA','ATENCIÓN ALTA')]

VAC = {
    'ale':'3–21 ago','andrea':'3–21 ago','javi':'3–21 ago',
    'paula':'22 jun – 21 ago','sara':'3–21 ago','cristina':'20 jul – 10 ago',
    'olatz':'17–28 ago','sofia':'10–24 ago','naiara':'6–10 jul · 17–21 ago',
    'marta':'3–7 ago','jesus':'13–31 jul',
}
RENDERS_FLUJO = [
    {'fase':'F1','titulo':'Volumetría y capturas','desc':'Planos + 3D + vistas marcadas. ~1 semana desde doc completa.'},
    {'fase':'F2','titulo':'Materialidad y acabados','desc':'Toda la info de acabados y mobiliario. 2–3 días.'},
    {'fase':'F3','titulo':'Render final','desc':'TODAS las correcciones cerradas ANTES de renderizar.'},
]
RENDERS_REGLAS = [
    'Máx. 2–3 proyectos activos simultáneos por renderista.',
    'Nunca activar sin documentación 100% completa.',
    'PM es el filtro — nadie pasa trabajo sin visto bueno del PM.',
]
MONTAJES = ALE_MONTAJES if ALE_MONTAJES else [
    {'fechas':'6–10 jul','proj':'Camino Sur 70','equipo':'Cristina / Olatz','dept':'Vivienda'},
    {'fechas':'6–14 jul','proj':'Pedraza 1º','equipo':'Olatz + Paula','dept':'Vivienda'},
]
AGENDA = [{'when': a['when'], 'text': f"{a['proj']} — {a['text']}"} for a in ALE_HITOS[:8]] if ALE_HITOS else []

# ── GENERAR DATA JS ────────────────────────────────────────────────────────────
DATA_JS = f"""
const WEEK_LABELS = {json.dumps(WEEK_LABELS)};
const MONTHS = {json.dumps(MONTHS)};
const TODAY_WEEK = {TODAY_WEEK};
const WEEK_LABEL = 'Semana {hoy.strftime("%d %b %Y")}';
const WEEK_STAMP = 'SEM {hoy.strftime("%d-%m-%Y")}';
const UPDATED = 'Actualizado {hoy.strftime("%d %b %Y")}';
const MASTER = {json.dumps(MASTER, ensure_ascii=False)};
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
const RENDERS_VAC = 'Renders vacaciones 1-15 agosto.';
const FOCO_SEMANA = {json.dumps(FOCO_SEMANA, ensure_ascii=False)};
const PROJS_PERSONA = {json.dumps(PROJS_PERSONA, ensure_ascii=False)};
const DEPT_PERSONA = {json.dumps(DEPT_PERSONA, ensure_ascii=False)};
const NOMBRE_PERSONA = {json.dumps(NOMBRE_PERSONA, ensure_ascii=False)};
const VAC = {json.dumps(VAC, ensure_ascii=False)};
const DEPT_SECTIONS = {json.dumps(DEPT_SECTIONS, ensure_ascii=False)};
const PERSON_ORDER = {json.dumps(PERSON_ORDER)};
"""

# ── LEER HEAD Y APP_JS DE ARCHIVOS SEPARADOS ──────────────────────────────────
import re
head_html = open(os.path.join(BASE, 'head.html'), encoding='utf-8').read()
app_js    = open(os.path.join(BASE, 'app.js'),   encoding='utf-8').read()

def escape_script_close(s):
    # Evita que un '</script' dentro de un texto libre (nota, bloqueador, hito...)
    # cierre prematuramente la etiqueta <script> y rompa el HTML generado.
    return s.replace('</script', '<\\/script')

html_out = (head_html +
    '<script>\n' + escape_script_close(DATA_JS) + '\n</script>\n' +
    '<script>\n' + app_js + '\n</script>\n' +
    '</body>\n</html>')

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html_out)

print(f"\nApp generada: {OUT}")
print(f"Proyectos: {len(MASTER)} | Alertas: {len(ALERTAS_JSON)} | Renders: {len(RENDERS)} | Personas: {len(PERSON_ORDER)}")
