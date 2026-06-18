#!/usr/bin/env python3
"""
APDS PM Estudio — Generador de app
Lee PM_ESTUDIO_MASTER_COMPLETO.xlsx y genera PM_Estudio_App.html
Uso: python generate_app.py
"""

import openpyxl
import json
import os
from datetime import datetime

EXCEL_PATH = os.path.join(os.path.dirname(__file__), 'PM_ESTUDIO_MASTER_COMPLETO.xlsx')
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'docs', 'index.html')

# ── LEER EXCEL ──────────────────────────────────────────────────────────────
wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)

WEEK_LABELS = ['18-22M','25-29M','1-5J','8-12J','15-19J','22-26J','29J-3Jl',
               '6-10Jl','13-17Jl','20-24Jl','27-31Jl','3-7A','10-14A',
               '17-21A','24-28A','31A-4S','7-11S','14-18S','21-25S','28-2O']

# Calcular semana actual (TODAY_WEEK)
# Semanas desde 18 mayo 2026
from datetime import date
semana_inicio = date(2026, 5, 18)
hoy = date.today()
diff = (hoy - semana_inicio).days // 7
TODAY_WEEK = max(0, min(diff, 19))
WEEK_LABEL_HOY = f"Semana {hoy.strftime('%d %b %Y')}"
WEEK_STAMP_HOY = f"SEM {hoy.strftime('%d·%m·%Y')}"
UPDATED = f"Actualizado {hoy.strftime('%d %b %Y')}"

# ── MASTER GLOBAL ────────────────────────────────────────────────────────────
def extract_master():
    ws = wb['MASTER GLOBAL']
    projects = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] and isinstance(row[0], str) and len(row[0].strip()) > 1:
            projects.append({
                'nombre': row[0].strip(),
                'resp': str(row[1] or '—').strip(),
                'estado': str(row[2] or '—').strip(),
                'intensidad': str(row[3] or '—').strip(),
                'hito': str(row[4] or '—').strip(),
                'riesgo': str(row[5] or '—').strip(),
                'obs': str(row[6] or '').strip(),
                'tl': {}
            })
    return projects

# ── TIMELINES ────────────────────────────────────────────────────────────────
def extract_tl(sheet_name, name_col, data_col, num_weeks=20):
    ws = wb[sheet_name]
    tl = {}
    SKIP = {'PROYECTO','EQUIPO','FECHAS','ESTADO','PLAN','PREVISIONES','LUNES',
            'MARTES','JUNIO','JULIO','MAYO','AGOSTO','SEPTIEMBRE','ESTA SEMANA',
            'ALICIA','OLATZ','SARA','ANDREA','CRISTINA','PAULA','MARTA','ALE',
            'JESUS','NELA','SEMANA QUE VIENE','PLANIFICACION','INICIO','DECO',
            'MONTAJE','OBRA'}
    for row in ws.iter_rows(values_only=True):
        n = row[name_col] if name_col < len(row) else None
        if not n or not isinstance(n, str): continue
        n = n.strip().upper()
        if len(n) < 3 or any(n.startswith(s) for s in SKIP): continue
        phases = {}
        for i in range(num_weeks):
            c = data_col + i
            if c < len(row) and row[c] and str(row[c]).strip():
                phases[i] = str(row[c]).strip()
        if phases:
            tl[n] = phases
    return tl

tl_viv  = extract_tl('VIVIENDA',   1, 7)
tl_hot  = extract_tl('HOTELES',    0, 7)
tl_rest = extract_tl('RESTAURANTES', 0, 7)
all_tl  = {**tl_viv, **tl_hot, **tl_rest}

# Asignar timelines a proyectos del master
MASTER = extract_master()
for p in MASTER:
    nombre_up = p['nombre'].upper()
    for key, phases in all_tl.items():
        if key in nombre_up or nombre_up in key or nombre_up[:10] in key:
            p['tl'] = phases
            break

# ── VACACIONES ───────────────────────────────────────────────────────────────
def extract_vac():
    ws = wb['VACACIONES VERANO']
    # Simplificado: leer las vacaciones conocidas
    return {
        'ale':     '15–19 jun · 3–21 ago',
        'andrea':  '15–19 jun · 3–21 ago',
        'javi':    '3–21 ago',
        'paula':   '22 jun – 21 ago',
        'sara':    '3–21 ago · 4–11 sep',
        'cristina':'20 jul – 10 ago',
        'olatz':   '17–28 ago',
        'sofia':   '10–24 ago',
        'laia':    '3–14 ago',
        'naiara':  '6–10 jul · 17–21 ago',
        'marta':   '3–7 ago',
        'jesus':   '13–31 jul',
    }

VAC = extract_vac()

# ── DATOS ESTÁTICOS (se actualizan manualmente cada semana) ─────────────────
FOCO_SEMANA = {
    'alicia':  ['Pedidos Pedraza','Antic Colonial','Feedback deco Alcalá','Feedback Hermosilla'],
    'olatz':   ['Actualización deco Pedraza','Avance deco Camino Sur 70','Revisión Gamal'],
    'sara':    ['Preparar deco Santander','Presentación Ibiza'],
    'andrea':  ['Remates y mobiliario Abubilla','Pedidos Valencia'],
    'cristina':['Pedidos Camino Sur 70'],
    'paula':   ['Fecha Pedro Valdivia','Revisión Valcarce'],
    'marta':   ['Visita Bilbao / Valencia'],
    'jesus':   ['Roca Maya — ZZCC','Vía 66 — arranque obra'],
    'ale':     ['Bernabéu — reunión presupuesto','Rubaiyat — seguimiento','Vía 66 — arranque'],
    'javi':    ['Coordinar semana','Revisar alertas críticas','Actualizar planning verano'],
    'sofia':   ['Joann — renders semanales','Cobue — seguimiento','Puerto Rico — cierre económico'],
    'laia':    ['Altheon — cerrar presentación','Hipódromo — valoración mobiliario'],
    'naiara':  ['Rubaiyat — montaje'],
    'nela':    ['Montesquinza — avance proyecto'],
}

PROJS_PERSONA = {
    'javi':    ['PASEO DE LOS LAGOS 132','ALCALÁ 58'],
    'alicia':  ['PEDRAZA','PASEO DE LOS LAGOS 105','HERMOSILLA','TORRE VALENCIA','ALCALÁ 58'],
    'olatz':   ['CAMINO SUR 70','PEDRAZA','VIV GAMAL STO DOMINGO','VIVIENDA PALOMA'],
    'paula':   ['ZAHARA','LA FLORIDA','TEPEYAC','TORRE VALENCIA'],
    'sara':    ['VALENCIA','VIUDA DE ALDAMA','SANTANDER','IBIZA','MONTESQUINZA'],
    'andrea':  ['VIVIENDA PALOMA','VALENCIA','MONTESQUINZA'],
    'cristina':['CAMINO SUR 70','LA RINCONADA'],
    'nela':    ['MONTESQUINZA'],
    'sofia':   ['PASEO DE LOS LAGOS 132','VIV GAMAL STO DOMINGO','FOX','PUERTO RICO'],
    'laia':    ['FOX','BERNABEU','BERNABÉU','MALLORCA SEVILLA'],
    'naiara':  ['FOX','BERNABEU','BERNABÉU','RUBAIYAT'],
    'marta':   ['DON RAMÓN','DON RAMON','ONE SHOT BILBAO'],
    'jesus':   ['ONE SHOT BILBAO','ROCA MAYA','VÍA 66','VIA 66','MARTÍNEZ CAMPOS'],
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

PERSON_ORDER = ['javi','ale','alicia','olatz','paula','sara','andrea',
                'cristina','nela','sofia','laia','naiara','marta','jesus']

CHALLAN = [
    {'prio':'URGENTE','proj':'Lagos 132','resp':'Sofía / PM','fase':'F1→F2','estado':'Reunión realizada ✅ Pendiente feedback para avanzar a F2','comprometida':'Por definir','realista':'Pendiente','next':'Dar feedback — ¿avanzamos a F2?','riesgo':'CRITICO'},
    {'prio':'URGENTE','proj':'Viuda de Aldama','resp':'Sara / Cristina','fase':'F1 correcciones','estado':'Reunión clientes realizada. Pendiente enviar paquete de correcciones','comprometida':'2–3 semanas','realista':'Sem 23–27 jun','next':'Enviar paquete en un solo envío','riesgo':'ALTO'},
    {'prio':'URGENTE','proj':'Joann','resp':'Sofía','fase':'R1→R2→R3 semanal','estado':'Entrada ✅ Salón esta sem · Comedor 29 jun','comprometida':'15/22/29 jun','realista':'⚠ Ritmo semanal satura Challan','next':'Renegociar a bloques 2–3 sem','riesgo':'ALTO'},
    {'prio':'MEDIO','proj':'La Rinconada','resp':'Cristina','fase':'F1 en curso','estado':'Challan arrancó esta semana. 1 espacio','comprometida':'Esta semana','realista':'Esta semana','next':'Capturas disponibles esta semana','riesgo':'MEDIO'},
]

ALERTAS = [
    {'proj':'Conflicto Paula/Olatz · julio','dept':'Vivienda','resp':'Paula / Olatz','text':'Paula tiene Zahara (13–15 jul) solapado con Pedraza 2º montaje (15–24 jul). Olatz tiene ese mismo montaje solapado con Gamal RD (desde 15 jul).','fecha':'Antes de jul','risk':'CRITICO'},
    {'proj':'Bernabéu — 3ª persona','dept':'Restaurantes','resp':'Laia / Naiara','text':'Laia y Naiara no coinciden disponibles ninguna semana de agosto. Sin 3ª persona el montaje no puede hacerse.','fecha':'Urgente','risk':'CRITICO'},
    {'proj':'Zahara — riesgo Raúl','dept':'Vivienda','resp':'Paula','text':'Raúl puede no terminar la obra a tiempo para el montaje 13–15 jul.','fecha':'Esta semana','risk':'CRITICO'},
]

MONTAJES = [
    {'fechas':'6–10 jul','proj':'Camino Sur 70','equipo':'Cristina / Olatz','dept':'Vivienda'},
    {'fechas':'6–14 jul','proj':'Pedraza 1º','equipo':'Olatz + Paula','dept':'Vivienda'},
    {'fechas':'13–15 jul','proj':'Zahara','equipo':'Paula + Alejandra','dept':'Vivienda'},
    {'fechas':'13–26 jul','proj':'Gamal RD','equipo':'Sofía · Olatz · Alejandra','dept':'Vivienda'},
    {'fechas':'21–24 jul','proj':'Valencia','equipo':'Sara + Andrea + Alejandra','dept':'Vivienda'},
    {'fechas':'24–28 ago','proj':'Don Ramón','equipo':'Marta','dept':'Hoteles'},
]

# ── GENERAR HTML ─────────────────────────────────────────────────────────────
HTML = open(os.path.join(os.path.dirname(__file__), 'app_template.html'), encoding='utf-8').read()

data_js = f"""
const WEEK_LABELS = {json.dumps(WEEK_LABELS)};
const MONTHS = [["MAY",0,1],["JUN",2,5],["JUL",6,10],["AGO",11,14],["SEP",15,18]];
const TODAY_WEEK = {TODAY_WEEK};
const WEEK_LABEL = "{WEEK_LABEL_HOY}";
const WEEK_STAMP = "{WEEK_STAMP_HOY}";
const UPDATED = "{UPDATED}";
const MASTER = {json.dumps(MASTER, ensure_ascii=False)};
const ALERTAS = {json.dumps(ALERTAS, ensure_ascii=False)};
const MONTAJES = {json.dumps(MONTAJES, ensure_ascii=False)};
const CHALLAN = {json.dumps(CHALLAN, ensure_ascii=False)};
const CHALLAN_VAC = "🏖 Challan de vacaciones 1–15 agosto — cualquier render previsto en agosto debe cerrarse ANTES del 1 ago.";
const CHALLAN_FLUJO = [{{"fase":"F1","titulo":"Volumetría y capturas","desc":"Planos + 3D + vistas marcadas. ~1 semana desde doc completa."}},{{"fase":"F2","titulo":"Materialidad y acabados","desc":"Toda la info de acabados y mobiliario. 2–3 días solo acabados · 1 semana si hay mobiliario."}},{{"fase":"F3","titulo":"Render final","desc":"TODAS las correcciones cerradas ANTES de renderizar. 2 días render + 1–2 días por ronda."}}];
const CHALLAN_REGLAS = ["Máx. 2–3 proyectos activos simultáneos con Challan.","Nunca activar sin documentación 100% completa.","PM es el filtro — nadie pasa trabajo sin visto bueno del PM.","Correcciones en un solo paquete — nunca por separado."];
const FOCO_SEMANA = {json.dumps(FOCO_SEMANA, ensure_ascii=False)};
const PROJS_PERSONA = {json.dumps(PROJS_PERSONA, ensure_ascii=False)};
const DEPT_PERSONA = {json.dumps(DEPT_PERSONA, ensure_ascii=False)};
const NOMBRE_PERSONA = {json.dumps(NOMBRE_PERSONA, ensure_ascii=False)};
const VAC = {json.dumps(VAC, ensure_ascii=False)};
const PERSON_ORDER = {json.dumps(PERSON_ORDER)};
"""

html_out = HTML.replace('__DATA_PLACEHOLDER__', data_js)

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(html_out)

print(f"✅ App generada: {OUTPUT_PATH}")
print(f"   Proyectos: {len(MASTER)}")
print(f"   Semana actual: semana índice {TODAY_WEEK}")
print(f"   Actualizado: {UPDATED}")
