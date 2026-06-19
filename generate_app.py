#!/usr/bin/env python3
"""
APDS PM Estudio — Generador de app
Lee PM_ESTUDIO_MASTER_COMPLETO.xlsx y genera docs/index.html
Uso: python generate_app.py
"""
import openpyxl, json, os
from datetime import date

BASE = os.path.dirname(os.path.abspath(__file__))
EXCEL = os.path.join(BASE, 'PM_ESTUDIO_MASTER_COMPLETO.xlsx')
OUT   = os.path.join(BASE, 'docs', 'index.html')
HTML_BEFORE = open(os.path.join(BASE, 'app_template.html'), encoding='utf-8').read().split('__DATA_PLACEHOLDER__')[0] if os.path.exists(os.path.join(BASE, 'app_template.html')) and '__DATA_PLACEHOLDER__' in open(os.path.join(BASE, 'app_template.html'), encoding='utf-8').read() else '<!DOCTYPE html><html><body><script>'
HTML_AFTER = open(os.path.join(BASE, 'app_template.html'), encoding='utf-8').read().split('__DATA_PLACEHOLDER__')[1] if os.path.exists(os.path.join(BASE, 'app_template.html')) and '__DATA_PLACEHOLDER__' in open(os.path.join(BASE, 'app_template.html'), encoding='utf-8').read() else '</script></body></html>'

wb = openpyxl.load_workbook(EXCEL, data_only=True)
print("Hojas:", wb.sheetnames)

# ── Semana actual ─────────────────────────────────────────────────────────────
hoy = date.today()
sem_inicio = date(2026, 6, 17)  # semana 0 = 17-19 jun
TODAY_WEEK = max(0, min((hoy - sem_inicio).days // 7, 15))
WEEK_LABELS = ['17-19J','22-26J','29J-3Jl','6-10Jl','13-17Jl','20-24Jl',
               '27-31Jl','3-7A','10-14A','17-21A','24-28A','31A-4S',
               '7-11S','14-18S','21-25S','28-2O']
MONTHS = [["JUN",0,0],["JUL",1,5],["AGO",6,9],["SEP",10,13],["OCT",14,15]]

# ── MASTER GLOBAL ─────────────────────────────────────────────────────────────
def extract_master():
    ws = wb['📋 MASTER GLOBAL']
    projects, header = [], False
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=ws.max_column, values_only=True):
        if not any(c for c in row): continue
        if str(row[0] or '').strip() == 'PROYECTO':
            header = True; continue
        if not header or not row[0] or not isinstance(row[0], str): continue
        n = str(row[0]).strip()
        if n.startswith('▸') or n.startswith('—') or len(n) < 2: continue
        projects.append({
            'nombre': n, 'dept': str(row[1] or '').strip(),
            'resp': str(row[2] or '—').strip(),
            'estado': str(row[3] or '—').strip(),
            'hito': str(row[4] or '—').strip(),
            'fecha': str(row[5] or '—').strip(),
            'bloqueador': str(row[6] or '—').strip(),
            'constructora': str(row[7] or '—').strip(),
            'fase': str(row[8] or '—').strip(),
            'atencion': str(row[9] or '—').strip(),
            'nivel': str(row[10] or '—').strip(),
            'tl': {}
        })
    return projects

# ── TIMELINES ─────────────────────────────────────────────────────────────────
def extract_planning(sheet_name):
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=ws.max_column, values_only=True))
    week_cols, header_idx = {}, None
    for i, row in enumerate(rows):
        if str(row[0] or '').strip() == 'PROYECTO':
            header_idx = i
            for j in range(2, len(row)):
                c = row[j]
                if c and isinstance(c, str) and any(ch.isdigit() for ch in c):
                    week_cols[j] = j - 2  # índice 0-based
            break
    if not week_cols or header_idx is None:
        return {}
    tl = {}
    SKIP = {'PROYECTO','RESP.','FIN EST.','NIVEL','PROY B','PROY E','PROY DECO',
            'OBRA','PEDIDOS','MONTAJE','REUNIÓN','ENTREGA','ALEJANDRA','⚠ RIESGO','FUERA'}
    for row in rows[header_idx + 1:]:
        n = row[0]
        if not n or not isinstance(n, str): continue
        n = n.strip()
        if len(n) < 2 or n.startswith('▸') or n in SKIP: continue
        phases = {}
        for col, idx in week_cols.items():
            if col < len(row) and row[col] and str(row[col]).strip() not in {'None',''}:
                phases[idx] = str(row[col]).strip()
        if phases:
            tl[n.upper()] = phases
    return tl

tl_viv  = extract_planning('🏠 Planning Vivienda')
tl_hot  = extract_planning('🏨 Planning Hoteles')
tl_rest = extract_planning('🍽️ Planning Restaurantes')
all_tl  = {**tl_viv, **tl_hot, **tl_rest}
print(f"Timelines: {len(tl_viv)} viv, {len(tl_hot)} hot, {len(tl_rest)} rest")

MASTER = extract_master()
for p in MASTER:
    key = p['nombre'].upper()
    for k, phases in all_tl.items():
        if k == key or k in key or key in k:
            p['tl'] = phases; break
print(f"Proyectos: {len(MASTER)}, con timeline: {sum(1 for p in MASTER if p['tl'])}")

# ── FOCO POR PERSONA ──────────────────────────────────────────────────────────
def extract_foco():
    ws = wb['👤 FOCO POR PERSONA']
    NOMBRES = {'PM':'javi','Sofía':'sofia','Laia':'laia','Paula':'paula',
               'Sara':'sara','Naiara':'naiara','Olatz':'olatz','Marta':'marta',
               'Andrea':'andrea','Cristina':'cristina','Nela':'nela',
               'Jesús':'jesus','Alejandra — CEO':'ale'}
    foco = {}
    for row in ws.iter_rows(min_row=3, values_only=True):
        if not row[0]: continue
        pid = NOMBRES.get(str(row[0]).strip())
        if not pid: continue
        texto = str(row[3] or '').strip()
        items = []
        for seg in texto.replace(' · ', '\n').split('\n'):
            seg = seg.strip()
            if seg and len(seg) > 4:
                items.append(seg)
        foco[pid] = items[:6]
    return foco

FOCO = extract_foco()

# ── CHALLAN ───────────────────────────────────────────────────────────────────
def extract_challan():
    ws = wb['🎨 Renders Challan']
    challan, header = [], False
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=ws.max_column, values_only=True):
        if not any(c for c in row): continue
        if str(row[0] or '').strip() == 'PRIO':
            header = True; continue
        if not header: continue
        if not row[0] or not isinstance(row[0], str): continue
        prio_raw = str(row[0]).strip()
        if 'REGLA' in prio_raw.upper() or len(prio_raw) > 20: break
        prio = 'URGENTE' if '🔴' in prio_raw else 'MEDIO' if '🟠' in prio_raw else 'BAJO'
        riesgo = 'CRITICO' if prio == 'URGENTE' else 'MEDIO'
        challan.append({
            'prio': prio, 'proj': str(row[1] or '').strip(),
            'dept': str(row[2] or '').strip(), 'resp': str(row[3] or '').strip(),
            'fase': str(row[4] or '').strip(), 'estado': str(row[5] or '').strip(),
            'comprometida': str(row[7] or '').strip(),
            'realista': str(row[8] or '').strip(),
            'next': str(row[9] or '').strip(), 'riesgo': riesgo
        })
    return challan

CHALLAN = extract_challan()
print(f"Challan: {len(CHALLAN)} proyectos")

# ── ALERTAS desde Master Global ───────────────────────────────────────────────
ALERTAS = [p for p in MASTER if p['nivel'] in ('ATENCIÓN MÁXIMA', 'ATENCIÓN ALTA')]
ALERTAS_JSON = [{'proj': p['nombre'], 'dept': p['dept'], 'resp': p['resp'],
                 'text': p['hito'] + (' — ' + p['bloqueador'] if p['bloqueador'] != '—' else ''),
                 'fecha': p['fecha'], 'risk': 'CRITICO' if p['nivel'] == 'ATENCIÓN MÁXIMA' else 'ALTO'}
                for p in ALERTAS]

# ── STATIC DATA ───────────────────────────────────────────────────────────────
PROJS_PERSONA = {
    'javi':    ['LAGOS 132','ALCALÁ 58'],
    'alicia':  ['PEDRAZA','LAGOS 105','HERMOSILLA','TORRE VALENCIA','ALCALÁ 58'],
    'olatz':   ['CAMINO SUR 70','PEDRAZA','VIV GAMAL STO DOMINGO','VIV PALOMA RD'],
    'paula':   ['ZAHARA','LA FLORIDA','TEPEYAC','TORRE VALENCIA'],
    'sara':    ['VALENCIA','VIUDA ALDAMA','SANTANDER VIV','IBIZA','MONTESQUINZA'],
    'andrea':  ['VIV PALOMA RD','VALENCIA','MONTESQUINZA','LAGOS 105'],
    'cristina':['CAMINO SUR 70','LA RINCONADA'],
    'nela':    ['MONTESQUINZA','CAMINO SUR 35','HERMOSILLA'],
    'sofia':   ['LAGOS 132','VIV GAMAL STO DOMINGO','JOANN','FOX','PUERTO RICO','COBUE'],
    'laia':    ['FOX','BERNABÉU','ALTHEON','HIPÓDROMO','COBUE'],
    'naiara':  ['FOX','BERNABÉU','RUBAIYAT','HIPÓDROMO'],
    'marta':   ['DON RAMÓN','ONE SHOT BILBAO','VINCCI VALENCIA'],
    'jesus':   ['ONE SHOT BILBAO','ROCA MAYA','VÍA 66','MARTÍNEZ CAMPOS','PSN OFICINAS'],
    'ale':     [],
}
DEPT_PERSONA = {
    'javi':'todos','alicia':'Vivienda','olatz':'Vivienda','paula':'Vivienda',
    'sara':'Vivienda','andrea':'Vivienda','cristina':'Vivienda','nela':'Vivienda',
    'sofia':'Restaurantes','laia':'Restaurantes','naiara':'Restaurantes',
    'marta':'Hoteles','jesus':'Hoteles','ale':'todos',
}
NOMBRE_PERSONA = {
    'javi':'Javi','alicia':'Alicia','olatz':'Olatz','paula':'Paula','sara':'Sara',
    'andrea':'Andrea','cristina':'Cristina','nela':'Nela','sofia':'Sofía',
    'laia':'Laia','naiara':'Naiara','marta':'Marta','jesus':'Jesús','ale':'Alejandra',
}
VAC = {
    'ale':'15–19 jun · 3–21 ago','andrea':'15–19 jun · 3–21 ago',
    'javi':'3–21 ago','paula':'22 jun – 21 ago','sara':'3–21 ago',
    'cristina':'20 jul – 10 ago','olatz':'17–28 ago','sofia':'10–24 ago',
    'laia':'3–14 ago','naiara':'6–10 jul · 17–21 ago',
    'marta':'3–7 ago','jesus':'13–31 jul',
}
MONTAJES = [
    {'fechas':'6–10 jul','proj':'Camino Sur 70','equipo':'Cristina / Olatz','dept':'Vivienda'},
    {'fechas':'6–14 jul','proj':'Pedraza 1º','equipo':'Olatz + Paula','dept':'Vivienda'},
    {'fechas':'13–15 jul','proj':'Zahara','equipo':'Paula + Alejandra','dept':'Vivienda'},
    {'fechas':'13–26 jul','proj':'Gamal RD','equipo':'Sofía · Olatz · Alejandra','dept':'Vivienda'},
    {'fechas':'21–24 jul','proj':'Valencia','equipo':'Sara + Andrea + Alejandra','dept':'Vivienda'},
    {'fechas':'24–31 ago','proj':'Don Ramón','equipo':'Marta','dept':'Hoteles'},
]
PRESENCIA_ALE = [
    {'fecha':'Lun 22 jun','texto':'Presentación Altheon en Barcelona con Laia'},
    {'fecha':'25 jun','texto':'Viaje a Sevilla con Marta y Sara — Don Ramón'},
    {'fecha':'13–15 jul','texto':'Zahara — montaje'},
    {'fecha':'20 jul','texto':'Gamal RD — viaje a República Dominicana'},
    {'fecha':'21–24 jul','texto':'Valencia — entrega oficial con Sara y Andrea'},
    {'fecha':'15–19 jun · 3–21 ago','texto':'Vacaciones'},
]
PROXIMAS = [
    {'sem':'22 jun','alerta':'MEDIO','items':['Reunión Lagos 105 + Pedro (PM cliente)','Reunión Tepeyac (24 jun)','Visita PSN con Raúl','Paula de vacaciones desde lun 22','Altheon — presentación Barcelona (Laia + Alejandra)']},
    {'sem':'6–10 jul','alerta':'CRITICO','items':['🚨 MÁXIMOS MONTAJES: CaminoSur70 (6-10) + Pedraza 1º (6-14)','Gamal RD arranca el 13','Equipo muy distribuido']},
    {'sem':'13–17 jul','alerta':'CRITICO','items':['🚨 Zahara (13-15) + Pedraza 2º (15-24) + Gamal RD en curso','Jesús inicia vacaciones (13 jul)','Conflicto Olatz/Paula sin resolver']},
    {'sem':'20–24 jul','alerta':'ALTO','items':['Gamal RD (Alejandra entra 20)','Valencia montaje (21-24)','One Shot Bilbao (27-30, Marta)']},
    {'sem':'3–21 ago','alerta':'CRITICO','items':['Estudio muy reducido — vacaciones generalizadas','Bernabéu montaje agosto sin resolver','Challan vacaciones 1–15 ago ⚠']},
]
PERSON_ORDER = ['javi','ale','alicia','olatz','paula','sara','andrea',
                'cristina','nela','sofia','laia','naiara','marta','jesus']
CHALLAN_FLUJO = [
    {'fase':'F1','titulo':'Volumetría y capturas','desc':'Planos + 3D + vistas marcadas. ~1 semana desde doc completa. Capturas IA internas primero → reunión cliente para definir dirección.'},
    {'fase':'F2','titulo':'Materialidad y acabados','desc':'Toda la info de acabados y mobiliario. 2–3 días solo acabados · 1 semana si hay mobiliario. Cambios: 1–2 días/ronda.'},
    {'fase':'F3','titulo':'Render final','desc':'TODAS las correcciones cerradas ANTES de renderizar. 2 días render + 1–2 días por ronda adicional.'},
]
CHALLAN_REGLAS = [
    'Máx. 2–3 proyectos activos simultáneos con Challan.',
    'Nunca activar sin documentación 100% completa.',
    'PM es el filtro — nadie pasa trabajo sin visto bueno del PM.',
    'Correcciones en un solo paquete — nunca por separado.',
    'Antes de F3: confirmar que no hay más correcciones pendientes.',
    'Al firmar contrato con renders: verificar cola y validar fecha realista ANTES de comprometerse.',
]

# ── GENERAR DATA JS ───────────────────────────────────────────────────────────
DATA_JS = f"""
const WEEK_LABELS = {json.dumps(WEEK_LABELS)};
const MONTHS = {json.dumps(MONTHS)};
const TODAY_WEEK = {TODAY_WEEK};
const WEEK_LABEL = "Semana {hoy.strftime('%d %b %Y')}";
const WEEK_STAMP = "SEM {hoy.strftime('%d·%m·%Y')}";
const UPDATED = "Actualizado {hoy.strftime('%d %b %Y')}";
const MASTER = {json.dumps(MASTER, ensure_ascii=False)};
const ALERTAS = {json.dumps(ALERTAS_JSON, ensure_ascii=False)};
const MONTAJES = {json.dumps(MONTAJES, ensure_ascii=False)};
const PRESENCIA_ALE = {json.dumps(PRESENCIA_ALE, ensure_ascii=False)};
const PROXIMAS = {json.dumps(PROXIMAS, ensure_ascii=False)};
const CHALLAN = {json.dumps(CHALLAN, ensure_ascii=False)};
const CHALLAN_FLUJO = {json.dumps(CHALLAN_FLUJO, ensure_ascii=False)};
const CHALLAN_REGLAS = {json.dumps(CHALLAN_REGLAS, ensure_ascii=False)};
const CHALLAN_VAC = "🏖 Challan de vacaciones 1–15 agosto — cualquier render previsto en agosto debe cerrarse ANTES del 1 ago.";
const FOCO_SEMANA = {json.dumps(FOCO, ensure_ascii=False)};
const PROJS_PERSONA = {json.dumps(PROJS_PERSONA, ensure_ascii=False)};
const DEPT_PERSONA = {json.dumps(DEPT_PERSONA, ensure_ascii=False)};
const NOMBRE_PERSONA = {json.dumps(NOMBRE_PERSONA, ensure_ascii=False)};
const VAC = {json.dumps(VAC, ensure_ascii=False)};
const PERSON_ORDER = {json.dumps(PERSON_ORDER)};
"""

# ── COMBINAR CON TEMPLATE ─────────────────────────────────────────────────────
html_out = '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>APDS PM Estudio</title></head><body><script>' + DATA_JS + '</script></body></html>'

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html_out)

print(f"\n✅ App generada: {OUT}")
print(f"   Proyectos: {len(MASTER)} | Con timeline: {sum(1 for p in MASTER if p['tl'])}")
print(f"   Alertas: {len(ALERTAS_JSON)} | Challan: {len(CHALLAN)} | Foco: {len(FOCO)} personas")
print(f"   Semana índice: {TODAY_WEEK} | Actualizado: {hoy}")
