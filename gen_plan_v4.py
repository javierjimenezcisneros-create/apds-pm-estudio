"""
APDS gen_plan_v4.py — Motor limpio según arquitectura validada 11 sep 2026

ARQUITECTURA:
  MASTER GLOBAL → estado actual + retroplanning fields
  GANTT MANUAL  → planificación explícita (prioridad absoluta)
  RETROPLANNING → calcula alertas (nunca modifica Gantt)

REGLAS FUNDAMENTALES:
  - Sin fill_between. Celda vacía = sin dato. Punto.
  - La fase del Master NO genera barras futuras.
  - El retroplanning genera alertas, no actividades.
  - Prioridad: Gantt manual > todo lo demás.
"""

# ══════════════════════════════════════════════════════════════════════════════
# PASO 1 — MOTOR DE CELDAS
# ══════════════════════════════════════════════════════════════════════════════
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Flowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from datetime import date, datetime
import urllib.request, openpyxl, io, sys, os

PAGE = landscape(A3)
W, H = float(PAGE[0]), float(PAGE[1])
MARGIN = 5*mm

# ── Paleta base ───────────────────────────────────────────────────────────────
GRANATE = colors.HexColor("#5C1831")
NARANJA = colors.HexColor("#C26942")
PAPER   = colors.HexColor("#F4F1EC")
BLANCO  = colors.white
GRIS    = colors.HexColor("#4A4A4A")
GRIS_L  = colors.HexColor("#9C9088")
ALERTA_C = colors.HexColor("#C62828")   # rojo alerta
ATEN_C   = colors.HexColor("#E07030")   # naranja atención
PREV_C   = colors.HexColor("#B8860B")   # dorado previsión

# ── Actividades (duración ≥1 semana) ─────────────────────────────────────────
ACTIVIDADES = {
    "PROY B":    "#BDD7EE",
    "PROY E":    "#70B0D8",
    "PROY DECO": "#C9B8E8",
    "ANT.PROY":  "#D4C4F0",
    "OBRA":      "#E8924A",
    "PEDIDOS":   "#FFE384",
    "MONTAJE":   "#E87878",
    "REMATES":   "#F5DE7A",
    "RENDERS":   "#C8C8C8",
    "PDTE LIC":  "#D0CEC8",
    "SUPERVISIÓN":"#E8E4E0",
}

# ── Hitos (puntuales) ─────────────────────────────────────────────────────────
HITOS = {
    "FIN OBRA":    "#C62828",
    "ENTREGA":     "#5FAD5F",
    "APERTURA":    "#5FAD5F",
    "PREENTREGA":  "#A8D8A8",
    "REUNIÓN":     "#A8D8A8",
    "REUNIÓN CL.": "#A8D8A8",
    "VISITA":      "#A8D8A8",
    "VALORACIÓN":  "#BDD7EE",
    "ALEJANDRA":   "#8B2252",
    "VIAJE":       "#8B2252",
    "REVISIÓN":    "#BDD7EE",
    "⚠":           "#FF4040",
}

TEXTO_BLANCO = {"FIN OBRA","ENTREGA","APERTURA","ALEJANDRA","VIAJE","PROY E","⚠"}
ALL_COLORS = {**ACTIVIDADES, **HITOS}

def get_color(txt):
    if not txt: return None
    t = txt.strip().upper()
    for k,v in ALL_COLORS.items():
        if k == t: return colors.HexColor(v)
    return None

def clasificar(txt):
    """Devuelve ('actividad'|'hito'|None, txt_normalizado)"""
    if not txt or txt.strip() in ('','—','None'): return None, ''
    t = txt.strip().upper()
    for k in ACTIVIDADES:
        if k == t: return 'actividad', k
    for k in HITOS:
        if k == t: return 'hito', k
    return 'actividad', t  # si no reconoce, tratar como actividad

# ── Celda: Actividad sola ─────────────────────────────────────────────────────
class ActCell(Flowable):
    def __init__(self, txt, alerta, w, h):
        super().__init__()
        self.txt = txt; self.alerta = alerta
        self.width = w; self.height = h

    def draw(self):
        c = self.canv; w,h = self.width, self.height
        bg = get_color(self.txt) or colors.HexColor("#EEEEEE")
        # Zona principal (actividad)
        alert_h = 2.8*mm if self.alerta else 0
        main_h = h - alert_h
        c.setFillColor(bg)
        c.rect(0, alert_h, w, main_h, fill=1, stroke=0)
        # Texto actividad
        tc = colors.white if self.txt in TEXTO_BLANCO else colors.HexColor("#2A2A2A")
        c.setFillColor(tc); c.setFont("Helvetica-Bold", 5.5)
        c.drawCentredString(w/2, alert_h + main_h*0.3, self.txt[:8])
        # Franja alerta inferior
        if self.alerta:
            lvl = self.alerta.split(':')[0] if ':' in self.alerta else 'ACCIÓN'
            ac = ALERTA_C if 'RIESGO' in lvl or 'ACCIÓN' in lvl else \
                 ATEN_C  if 'ATENCIÓN' in lvl else PREV_C
            c.setFillColor(ac)
            c.rect(0, 0, w, alert_h, fill=1, stroke=0)
            c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 4.5)
            txt_a = self.alerta.replace('ACCIÓN:','⚠').replace('ATENCIÓN:','●').replace('RIESGO:','⚠')
            c.drawString(1.5, 0.6, txt_a[:16])

# ── Celda: Hito solo ──────────────────────────────────────────────────────────
class HitoCell(Flowable):
    def __init__(self, txt, alerta, w, h):
        super().__init__()
        self.txt = txt; self.alerta = alerta
        self.width = w; self.height = h

    def draw(self):
        c = self.canv; w,h = self.width, self.height
        bg = get_color(self.txt) or colors.HexColor("#CCCCCC")
        alert_h = 2.8*mm if self.alerta else 0
        main_h = h - alert_h
        c.setFillColor(bg)
        c.rect(0, alert_h, w, main_h, fill=1, stroke=0)
        tc = colors.white if self.txt in TEXTO_BLANCO else colors.HexColor("#2A2A2A")
        c.setFillColor(tc); c.setFont("Helvetica-Bold", 5.5)
        c.drawCentredString(w/2, alert_h + main_h*0.3, self.txt[:8])
        if self.alerta:
            lvl = self.alerta.split(':')[0] if ':' in self.alerta else 'ACCIÓN'
            ac = ALERTA_C if 'RIESGO' in lvl or 'ACCIÓN' in lvl else \
                 ATEN_C  if 'ATENCIÓN' in lvl else PREV_C
            c.setFillColor(ac)
            c.rect(0, 0, w, alert_h, fill=1, stroke=0)
            c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 4.5)
            txt_a = self.alerta.replace('ACCIÓN:','⚠').replace('ATENCIÓN:','●').replace('RIESGO:','⚠')
            c.drawString(1.5, 0.6, txt_a[:16])

# ── Celda: Actividad + Hito (diagonal) ───────────────────────────────────────
class DiagCell(Flowable):
    def __init__(self, act_txt, hito_txt, alerta, w, h):
        super().__init__()
        self.act = act_txt; self.hito = hito_txt; self.alerta = alerta
        self.width = w; self.height = h

    def draw(self):
        c = self.canv; w,h = self.width, self.height
        alert_h = 2.8*mm if self.alerta else 0
        main_h = h - alert_h
        ac = get_color(self.act)  or colors.HexColor("#EEEEEE")
        hc = get_color(self.hito) or colors.HexColor("#CCCCCC")
        y0 = alert_h
        # Triángulo superior-izquierda (actividad)
        c.setFillColor(ac)
        path = c.beginPath()
        path.moveTo(0, y0); path.lineTo(w, y0+main_h); path.lineTo(0, y0+main_h); path.close()
        c.drawPath(path, fill=1, stroke=0)
        # Triángulo inferior-derecha (hito)
        c.setFillColor(hc)
        path = c.beginPath()
        path.moveTo(0, y0); path.lineTo(w, y0); path.lineTo(w, y0+main_h); path.close()
        c.drawPath(path, fill=1, stroke=0)
        # Línea diagonal
        c.setStrokeColor(colors.white); c.setLineWidth(0.8)
        c.line(0, y0, w, y0+main_h)
        # Texto actividad (arriba-izq)
        tc_a = colors.white if self.act in TEXTO_BLANCO else colors.HexColor("#2A2A2A")
        c.setFillColor(tc_a); c.setFont("Helvetica-Bold", 5)
        c.drawString(1.5, y0+main_h*0.62, self.act[:6])
        # Texto hito (abajo-der)
        tc_h = colors.white if self.hito in TEXTO_BLANCO else colors.HexColor("#2A2A2A")
        c.setFillColor(tc_h)
        c.drawRightString(w-1.5, y0+main_h*0.08, self.hito[:6])
        # Franja alerta
        if self.alerta:
            lvl = self.alerta.split(':')[0] if ':' in self.alerta else 'ACCIÓN'
            ac2 = ALERTA_C if 'RIESGO' in lvl or 'ACCIÓN' in lvl else \
                  ATEN_C  if 'ATENCIÓN' in lvl else PREV_C
            c.setFillColor(ac2)
            c.rect(0, 0, w, alert_h, fill=1, stroke=0)
            c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 4.5)
            txt_al = self.alerta.replace('ACCIÓN:','⚠').replace('ATENCIÓN:','●').replace('RIESGO:','⚠')
            c.drawString(1.5, 0.6, txt_al[:16])

# ── Celda: Vacía con alerta ───────────────────────────────────────────────────
class AlertaCell(Flowable):
    """Celda vacía pero con alerta de retroplanning visible."""
    def __init__(self, alerta, w, h):
        super().__init__()
        self.alerta = alerta
        self.width = w; self.height = h

    def draw(self):
        c = self.canv; w,h = self.width, self.height
        alert_h = min(h, 3*mm)
        lvl = self.alerta.split(':')[0] if ':' in self.alerta else 'ACCIÓN'
        ac = ALERTA_C if 'RIESGO' in lvl or 'ACCIÓN' in lvl else \
             ATEN_C  if 'ATENCIÓN' in lvl else PREV_C
        # Fondo vacío (claro)
        bg = colors.HexColor("#FFF8F5") if 'RIESGO' in lvl or 'ACCIÓN' in lvl else \
             colors.HexColor("#FFFDF0")
        c.setFillColor(bg)
        c.rect(0, 0, w, h, fill=1, stroke=0)
        # Franja de alerta
        c.setFillColor(ac)
        c.rect(0, 0, w, alert_h, fill=1, stroke=0)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 4.5)
        txt_al = self.alerta.replace('ACCIÓN:','⚠').replace('ATENCIÓN:','●').replace('RIESGO:','⚠')
        c.drawString(1.5, 0.6, txt_al[:16])

def make_cell(gantt_txt, alerta, cell_w, cell_h):
    """
    Construye la celda correcta según el dato del Gantt y la alerta.
    gantt_txt: string del Excel ("OBRA", "VISITA", "OBRA|VISITA", "")
    alerta: string de retroplanning ("ACCIÓN: ⚠ PEDIDOS") o None
    """
    if not gantt_txt or gantt_txt.strip() in ('','—','None'):
        if alerta:
            return AlertaCell(alerta, cell_w, cell_h)
        return Paragraph("", ParagraphStyle('_'))

    parts = [t.strip() for t in gantt_txt.split('|')]

    if len(parts) >= 2:
        t1, t2 = parts[0], parts[1]
        tipo1, n1 = clasificar(t1)
        tipo2, n2 = clasificar(t2)
        # Asegurar actividad arriba, hito abajo
        if tipo1 == 'hito' and tipo2 == 'actividad':
            t1, t2 = t2, t1
        return DiagCell(t1, t2, alerta, cell_w, cell_h)

    single = parts[0]
    tipo, norm = clasificar(single)
    if tipo == 'hito':
        return HitoCell(single, alerta, cell_w, cell_h)
    else:
        return ActCell(single, alerta, cell_w, cell_h)

# ── Helper párrafo ────────────────────────────────────────────────────────────
def pp(text, size=7, bold=False, color=GRIS, align=TA_LEFT):
    fn = "Helvetica-Bold" if bold else "Helvetica"
    return Paragraph(str(text) if text else "",
        ParagraphStyle('_', fontName=fn, fontSize=size,
            textColor=color, leading=size*1.3, alignment=align))

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN TEMPORAL
# ══════════════════════════════════════════════════════════════════════════════
HOY = date.today()

# Semanas del planning departamental (9 semanas)
WEEKS = [
    ("SEP","9 SEP",  date(2026,9,9)),
    ("SEP","14 SEP", date(2026,9,14)),
    ("SEP","21 SEP", date(2026,9,21)),
    ("SEP","28 SEP", date(2026,9,28)),
    ("OCT","5 OCT",  date(2026,10,5)),
    ("OCT","12 OCT", date(2026,10,12)),
    ("OCT","19 OCT", date(2026,10,19)),
    ("OCT","26 OCT", date(2026,10,26)),
    ("NOV","2 NOV",  date(2026,11,2)),
]
N = len(WEEKS)
WEEK_LABEL_TO_IDX = {sem: i for i,(mes,sem,d) in enumerate(WEEKS)}
WEEK_DATES = [d for _,_,d in WEEKS]
MONTH_BREAKS = [3, 7]  # SEP→OCT, OCT→NOV

# Columnas
COL_N  = 8*mm
COL_F  = 4*mm
COL_P  = 34*mm
COL_R  = 14*mm
COL_NO = 56*mm
COL_FE = 11*mm
COL_RI = 14*mm
FIXED  = COL_N+COL_F+COL_P+COL_R+COL_NO+COL_FE+COL_RI
COL_W  = (W - 2*MARGIN - FIXED) / N
CELL_H = 7.5*mm

HOY_IDX = next((i for i,(m,s,d) in enumerate(WEEKS) if d <= HOY < (WEEKS[i+1][2] if i+1<N else date(2099,1,1))), 0)

COLS = [COL_N, COL_F, COL_P, COL_R] + [COL_W]*N + [COL_NO, COL_FE, COL_RI]

# ══════════════════════════════════════════════════════════════════════════════
# PASO 3 — MOTOR DE RETROPLANNING
# ══════════════════════════════════════════════════════════════════════════════
def parse_fecha(txt):
    """Intenta parsear una fecha de texto. Devuelve date o None."""
    if not txt or txt in ('—','','None','Pdte','2027','2026'): return None
    formatos = ['%d/%m/%Y','%d/%m/%y','%d %b %Y','%d %b %y',
                '%b %Y','%B %Y','%d de %B de %Y']
    meses_es = {'ene':'Jan','feb':'Feb','mar':'Mar','abr':'Apr','may':'May',
                'jun':'Jun','jul':'Jul','ago':'Aug','sep':'Sep','oct':'Oct',
                'nov':'Nov','dic':'Dec'}
    t = txt.strip().lower()
    for k,v in meses_es.items():
        t = t.replace(k, v)
    for fmt in formatos:
        try: return datetime.strptime(t.title(), fmt).date()
        except: pass
    return None

def semanas_entre(d1, d2):
    """Semanas naturales entre dos fechas."""
    if not d1 or not d2: return None
    return (d2 - d1).days // 7

def nivel_alerta(semanas_restantes):
    """Clasifica el nivel de urgencia según margen restante."""
    if semanas_restantes is None: return None
    if semanas_restantes < 0:   return "RIESGO"
    if semanas_restantes <= 2:  return "ACCIÓN"
    if semanas_restantes <= 5:  return "ATENCIÓN"
    if semanas_restantes <= 8:  return "PREVISIÓN"
    return None

def retroplanning_vivienda(proyecto):
    """
    Calcula alertas de retroplanning para proyectos de VIVIENDA.
    Solo cuando hay una fecha ancla (montaje o fin obra).
    Devuelve lista de alertas: [(week_idx, 'NIVEL: ⚠ TEXTO'), ...]
    """
    alertas = []
    
    montaje_txt   = proyecto.get('montaje_previsto','')
    fin_obra_txt  = proyecto.get('fin_obra','') or proyecto.get('fecha','')
    deco_cerrada  = proyecto.get('deco_cerrada','') in ('SÍ','SI','Sí','sí','si','yes','YES')
    presu_aceptado = proyecto.get('presupuesto_aceptado','') in ('SÍ','SI','Sí','sí','si','yes','YES')
    pedidos_conf  = proyecto.get('pedidos_confirmados','') in ('SÍ','SI','Sí','sí','si','yes','YES')
    
    # Fase activa según Gantt (si tiene PEDIDOS, MONTAJE, etc.)
    gantt = proyecto.get('gantt', {})  # {week_idx: txt}
    tiene_pedidos_gantt = any('PEDIDO' in str(v).upper() for v in gantt.values() if v)
    
    # Ancla temporal: montaje > fin obra
    fecha_ancla = parse_fecha(montaje_txt) or parse_fecha(fin_obra_txt)
    if not fecha_ancla:
        # Sin ancla: alerta solo si el proyecto necesita montaje
        estado = proyecto.get('estado','').upper()
        fase   = proyecto.get('fase_actual','').upper()
        if any(f in (estado+fase) for f in ('OBRA','DECO','PEDIDO','MONTAJE','REMATE')):
            if not proyecto.get('terminado', False):
                alertas.append((-1, "INFO: FALTA FECHA FIN OBRA / MONTAJE"))
        return alertas
    
    # Verificar información desactualizada
    if fecha_ancla < HOY:
        estado = proyecto.get('estado','').upper()
        if 'TERMINADO' not in estado and 'CERRADO' not in estado:
            alertas.append((-1, f"INFO: REVISAR FECHA (ancla {fecha_ancla.strftime('%d/%m')} < hoy)"))
        return alertas
    
    # Calcular hitos hacia atrás desde fecha_ancla
    semanas_a_ancla = semanas_entre(HOY, fecha_ancla)
    
    # 1. PEDIDOS — mínimo 12 semanas antes del montaje
    if not pedidos_conf and not tiene_pedidos_gantt:
        sw = semanas_a_ancla - 12
        nivel = nivel_alerta(sw)
        if nivel:
            # Calcular en qué semana del planning cae
            fecha_pedidos = date.fromordinal(fecha_ancla.toordinal() - 12*7)
            for i, (m,s,d) in enumerate(WEEKS):
                if abs((d - fecha_pedidos).days) <= 7:
                    alertas.append((i, f"{nivel}: ⚠ PEDIDOS"))
                    break
            else:
                if sw <= 0:
                    alertas.append((0, f"{nivel}: ⚠ PEDIDOS (urgente)"))

    # 2. PRESUPUESTO ACEPTADO — 14 semanas antes
    if not presu_aceptado and not pedidos_conf:
        sw = semanas_a_ancla - 14
        nivel = nivel_alerta(sw)
        if nivel and nivel in ("RIESGO","ACCIÓN"):
            fecha_presu = date.fromordinal(fecha_ancla.toordinal() - 14*7)
            for i, (m,s,d) in enumerate(WEEKS):
                if abs((d - fecha_presu).days) <= 7:
                    alertas.append((i, f"{nivel}: ⚠ PRESU ACEPTADO"))
                    break
            else:
                if sw <= 0:
                    alertas.append((0, f"{nivel}: ⚠ PRESU ACEPTADO"))

    # 3. DECO CERRADA — 16 semanas antes
    if not deco_cerrada:
        sw = semanas_a_ancla - 16
        nivel = nivel_alerta(sw)
        if nivel:
            fecha_deco = date.fromordinal(fecha_ancla.toordinal() - 16*7)
            for i, (m,s,d) in enumerate(WEEKS):
                if abs((d - fecha_deco).days) <= 7:
                    alertas.append((i, f"{nivel}: ⚠ CERRAR DECO"))
                    break
            else:
                if sw <= 0:
                    alertas.append((0, f"{nivel}: ⚠ CERRAR DECO"))

    # 4. Incompatibilidad temporal (Rubaiyat SP case)
    if semanas_a_ancla < 8:
        estado = proyecto.get('estado','').upper()
        fase   = proyecto.get('fase_actual','').upper()
        if 'ANT.PROY' in fase or 'ANTEPROY' in fase or 'PROY B' in fase:
            alertas.append((0, "RIESGO: ⚠ REVISAR VIABILIDAD"))

    return alertas

def retroplanning_restaurantes(proyecto):
    """Solo cuando el alcance incluye deco/montaje gestionado por Pombo."""
    gantt  = proyecto.get('gantt', {})
    tiene_montaje = any('MONTAJE' in str(v).upper() or 'APERTURA' in str(v).upper()
                        for v in gantt.values() if v)
    fecha_ancla = parse_fecha(proyecto.get('montaje_previsto','')) or \
                  parse_fecha(proyecto.get('fecha',''))
    
    alertas = []
    if not tiene_montaje and not fecha_ancla:
        return alertas
    
    if fecha_ancla and fecha_ancla >= HOY:
        semanas_a = semanas_entre(HOY, fecha_ancla)
        pedidos_conf = proyecto.get('pedidos_confirmados','') in ('SÍ','SI','Sí','sí')
        tiene_pedidos = any('PEDIDO' in str(v).upper() for v in gantt.values() if v)
        if not pedidos_conf and not tiene_pedidos and semanas_a <= 12:
            nivel = nivel_alerta(semanas_a - 8)
            if nivel:
                alertas.append((0, f"{nivel}: ⚠ PEDIDOS"))
    return alertas

def retroplanning_hoteles(proyecto):
    """Hoteles: supervisión, montajes (puede haber varios), carga, Alejandra."""
    alertas = []
    # Solo alertas básicas para hoteles — sin cadena de pedidos de vivienda
    fecha_ancla = parse_fecha(proyecto.get('montaje_previsto','')) or \
                  parse_fecha(proyecto.get('fecha',''))
    if fecha_ancla and HOY <= fecha_ancla:
        semanas_a = semanas_entre(HOY, fecha_ancla)
        if semanas_a <= 3:
            alertas.append((0, f"ACCIÓN: ⚠ MONTAJE EN {semanas_a}W"))
    return alertas

def calcular_alertas(proyecto):
    dept = proyecto.get('dept','').upper()
    if dept == 'VIVIENDA':     return retroplanning_vivienda(proyecto)
    if dept == 'RESTAURANTES': return retroplanning_restaurantes(proyecto)
    if dept == 'HOTELES':      return retroplanning_hoteles(proyecto)
    return []

# ══════════════════════════════════════════════════════════════════════════════
# PASO 4 — ORDEN DINÁMICO
# ══════════════════════════════════════════════════════════════════════════════
def score_proyecto(proyecto):
    """
    Score de prioridad (menor = más arriba).
    0: hito inminente esta/próxima semana
    1: alerta RIESGO activa
    2: alerta ACCIÓN activa + actividad
    3: alerta ATENCIÓN + actividad
    4: actividad activa + hito ≤4 sem
    5: actividad activa con fecha conocida
    6: seguimiento sin urgencia
    7: sin actividad / sin fecha
    8: parado / terminado
    """
    nivel = proyecto.get('nivel_atencion','SEGUIMIENTO').upper()
    gantt = proyecto.get('gantt', {})
    alertas = proyecto.get('alertas_calculadas', [])
    fecha_txt = proyecto.get('fecha','') or proyecto.get('fin_obra','')
    fecha = parse_fecha(fecha_txt)

    # Score base por estado
    if nivel == 'PARADO': return 8
    if proyecto.get('terminado', False): return 8

    # Hito inminente en las próximas 2 semanas
    hitos_inminen = [v for k,v in gantt.items()
                     if k in (0,1,2) and v and
                     any(h in str(v).upper() for h in
                         ('FIN OBRA','ENTREGA','MONTAJE','APERTURA','PREENTREGA'))]
    if hitos_inminen: return 0

    # Alertas activas
    has_riesgo = any('RIESGO' in (a[1] if len(a)>1 else '') for a in alertas)
    has_accion = any('ACCIÓN' in (a[1] if len(a)>1 else '') for a in alertas)
    has_atencion = any('ATENCIÓN' in (a[1] if len(a)>1 else '') for a in alertas)

    has_gantt = bool(gantt)

    if nivel == 'ATENCIÓN MÁXIMA' and has_riesgo: return 1
    if has_riesgo: return 1
    if has_accion and has_gantt: return 2
    if has_accion: return 2
    if has_atencion and has_gantt: return 3
    if nivel == 'ATENCIÓN ALTA': return 3

    # Actividad + fecha próxima
    if has_gantt and fecha and fecha <= date(HOY.year, HOY.month+2 if HOY.month<11 else 1, 1):
        return 4
    if has_gantt: return 5
    if fecha: return 6
    return 7

# ══════════════════════════════════════════════════════════════════════════════
# PASO 2 — LECTOR DEL EXCEL
# ══════════════════════════════════════════════════════════════════════════════
REPO  = "javierjimenezcisneros-create/apds-pm-estudio"
EXCEL = "PM_ESTUDIO_MASTER_COMPLETO.xlsx"

def download_excel():
    url = f"https://raw.githubusercontent.com/{REPO}/main/{EXCEL}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = r.read()
        print(f"✅ Excel descargado ({len(data)//1024}KB)")
        return openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    except Exception as e:
        if os.path.exists(EXCEL):
            print(f"⚠ Sin red — usando {EXCEL} local")
            return openpyxl.load_workbook(EXCEL, data_only=True)
        print(f"❌ {e}"); sys.exit(1)

def read_master(wb):
    """
    Lee MASTER GLOBAL. Devuelve dict nombre_upper → datos del proyecto.
    Incluye: fase_actual, estado, equipo, fecha, fin_obra, montaje_previsto,
             nivel_atencion, obs, bloqueador, deco_cerrada, presupuesto_aceptado,
             pedidos_confirmados, dept, terminado.
    """
    if 'MASTER GLOBAL' not in wb.sheetnames:
        print("⚠ Hoja MASTER GLOBAL no encontrada — continuando sin datos de Master")
        return {}
    ws = wb['MASTER GLOBAL']
    # Detectar cabecera
    header = {}
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if row[0] and str(row[0]).strip() == 'PROYECTO':
            for j, h in enumerate(row):
                if h: header[str(h).strip().upper()] = j
            break

    master = {}
    for row in ws.iter_rows(min_row=2+list(ws.iter_rows()).__len__() - ws.max_row,
                             values_only=True):
        pass  # just to find the right start

    # Leer todas las filas después de la cabecera
    header_found = False
    for row in ws.iter_rows(values_only=True):
        if not any(c for c in row if c): continue
        first = str(row[0] or '').strip()
        if first == 'PROYECTO':
            header_found = True
            for j, h in enumerate(row):
                if h: header[str(h).strip().upper()] = j
            continue
        if not header_found: continue
        if not row[0] or len(str(row[0]).strip()) < 2: continue
        nombre = str(row[0]).strip()
        if nombre.startswith('▸') or nombre.startswith('Actualiz'): continue

        def v(campo):
            idx = header.get(campo.upper(), -1)
            if idx < 0: return ''
            return str(row[idx] or '').strip() if idx < len(row) else ''

        estado = v('ESTADO')
        terminado = any(t in estado.upper() for t in
                        ('TERMINADO','CERRADO','FINALIZADO'))

        master[nombre.upper()] = {
            'nombre': nombre,
            'dept': v('DPTO') or v('DEPARTAMENTO') or v('DEPT'),
            'equipo': v('RESPONSABLE') or v('EQUIPO') or v('RESP'),
            'estado': estado,
            'fase_actual': v('FASE') or v('FASE ACTUAL'),
            'hito': v('HITO PRÓXIMO') or v('HITO') or v('PRÓXIMO HITO'),
            'fecha': v('FECHA') or v('FIN EST') or v('FIN EST.'),
            'fin_obra': v('FIN OBRA') or v('FIN_OBRA'),
            'montaje_previsto': v('MONTAJE') or v('MONTAJE PREVISTO'),
            'nivel_atencion': v('NIVEL') or v('ATENCIÓN') or 'SEGUIMIENTO',
            'obs': v('OBSERVACIONES') or v('OBS'),
            'bloqueador': v('BLOQUEADOR'),
            'deco_cerrada': v('DECO_CERRADA') or v('DECO CERRADA'),
            'presupuesto_aceptado': v('PRESUPUESTO_ACEPTADO') or v('PRESUPUESTO ACEPTADO'),
            'pedidos_confirmados': v('PEDIDOS_CONFIRMADOS') or v('PEDIDOS CONFIRMADOS'),
            'terminado': terminado,
        }
    print(f"   Master: {len(master)} proyectos")
    return master

def read_gantt_sheet(wb, sheet_name):
    """
    Lee una hoja de planning (VIVIENDA/REST/HOT).
    Devuelve dict nombre_upper → {week_idx: txt_celda}.
    SIN fill_between. Solo lo explícito.
    """
    if sheet_name not in wb.sheetnames:
        print(f"   ⚠ Hoja {sheet_name} no encontrada")
        return {}, []

    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    header_idx = None
    week_cols = {}  # col_idx → week_label

    for i, row in enumerate(rows):
        if len(row) > 1 and str(row[1] or '').strip() == 'PROYECTO':
            header_idx = i
            for j in range(6, len(row)):
                v = row[j]
                if v and isinstance(v, str) and any(c.isdigit() for c in str(v)):
                    week_cols[j] = str(v).strip()
            break

    if header_idx is None:
        return {}, []

    gantt   = {}
    ordered = []  # para preservar el orden del Excel

    for row in rows[header_idx+1:]:
        if not row: continue
        nombre = str(row[1] or '').strip() if len(row) > 1 else ''
        if not nombre or len(nombre) < 2: continue
        if nombre.startswith('▸') or nombre.startswith('  ') or \
           nombre in ('VACACIONES','🏖'): continue

        semanas = {}
        for j, wlabel in week_cols.items():
            idx = WEEK_LABEL_TO_IDX.get(wlabel, -1)
            if idx < 0: continue
            if j < len(row) and row[j] is not None:
                val = str(row[j]).strip()
                if val and val not in ('None','—',''):
                    semanas[idx] = val   # SIN inferencia, solo explícito

        is_latente = str(row[5] or '').strip().upper() == 'PARADO' if len(row)>5 else False
        gantt[nombre.upper()] = semanas
        ordered.append({
            'nombre': nombre,
            'codigo': str(row[0] or '').strip(),
            'equipo': str(row[2] or '').strip(),
            'nota':   str(row[3] or '').strip(),
            'fin_est':str(row[4] or '').strip(),
            'riesgo': str(row[5] or '').strip(),
            'gantt':  semanas,
            'is_latente': is_latente,
        })

    return gantt, ordered

def merge_capas(master, gantt_data, ordered, dept):
    """
    Combina Master + Gantt + Retroplanning.
    Devuelve lista de proyectos enriquecidos, ordenados por prioridad.
    """
    proyectos = []
    for item in ordered:
        nombre_key = item['nombre'].upper()
        master_data = master.get(nombre_key, {})

        # Enriquecer con datos del Master
        proyecto = {
            **item,
            'dept': dept,
            **{k: v for k,v in master_data.items() if v and k not in item},
        }
        # Asegurar que el gantt del master coincide con el del gantt sheet
        if not proyecto.get('gantt') and master_data.get('gantt'):
            proyecto['gantt'] = master_data['gantt']

        # Calcular alertas de retroplanning (NO modifican el gantt)
        if not item.get('is_latente') and not proyecto.get('terminado', False):
            alertas = calcular_alertas(proyecto)
            proyecto['alertas_calculadas'] = alertas
        else:
            proyecto['alertas_calculadas'] = []

        proyectos.append(proyecto)

    # Ordenar por score
    proyectos.sort(key=lambda x: (score_proyecto(x), x.get('nombre','')))
    return proyectos

# ══════════════════════════════════════════════════════════════════════════════
# PASO 5 — PLANNING DEPARTAMENTAL
# ══════════════════════════════════════════════════════════════════════════════
def p_row(proyecto):
    """Construye la fila de tabla para un proyecto."""
    nombre = proyecto.get('nombre','')
    codigo = proyecto.get('codigo','')
    equipo = proyecto.get('equipo','') or proyecto.get('resp','')
    nota   = proyecto.get('nota','') or proyecto.get('obs','')
    fin    = proyecto.get('fin_est','') or proyecto.get('fecha','')
    riesgo = proyecto.get('riesgo','') or proyecto.get('nivel_atencion','')
    gantt  = proyecto.get('gantt', {})
    alertas_calc = proyecto.get('alertas_calculadas', [])
    alert = '⚠' in str(nota) or riesgo in ('ATENCIÓN MÁXIMA',)

    # Mapa de alertas por semana
    alertas_por_sem = {}
    for item in alertas_calc:
        if isinstance(item, (list,tuple)) and len(item)==2:
            idx, txt = item
            if 0 <= idx < N:
                alertas_por_sem[idx] = txt

    nota_c = nota[:72]+'…' if len(nota)>72 else nota
    pc = colors.HexColor("#C0392B") if alert else GRANATE
    rc_map = {"ATENCIÓN ALTA": colors.HexColor("#E07030"),
              "ATENCIÓN MÁXIMA": colors.HexColor("#C0392B"),
              "SEGUIMIENTO": colors.HexColor("#1A5C1A"),
              "ESTABLE": colors.HexColor("#1A5C1A"),
              "PARADO": GRIS_L}
    rc = rc_map.get(riesgo, GRIS)
    rshort = {"ATENCIÓN MÁXIMA":"AT.MÁX","ATENCIÓN ALTA":"AT.ALTA",
               "SEGUIMIENTO":"SEGUIM.","ESTABLE":"OK","PARADO":"PARADO"}.get(riesgo, riesgo[:7])

    row = [
        pp(codigo, 6, False, GRIS_L, TA_CENTER),
        pp("", 6),   # franja fase
        pp(nombre, 8, True, pc),
        pp(equipo, 6.5, False, GRIS),
    ]
    for i,(mes,sem,d) in enumerate(WEEKS):
        gantt_txt = gantt.get(i,'')
        alerta    = alertas_por_sem.get(i)
        row.append(make_cell(gantt_txt, alerta, COL_W, CELL_H))
    row += [
        pp(nota_c, 6, False, GRIS),
        pp(fin,    6.5, False, GRIS, TA_CENTER),
        pp(rshort, 6, True, rc, TA_CENTER),
    ]
    return row

def sep_row(label):
    lbl = pp(f"  {label.upper()}", 6.5, True, colors.HexColor("#5C5248"), TA_LEFT)
    e   = pp("")
    return [e]*2 + [lbl] + [e]*(N+3)

def lat_row():
    lbl = pp("  LATENTES / PAUSADOS", 6.5, True, GRIS_L, TA_LEFT)
    e   = pp("")
    return [e]*2 + [lbl] + [e]*(N+3)

def make_headers(dept_color, dept_name):
    r0 = [pp("",6), pp(""), pp("",7,True,BLANCO,TA_CENTER), pp("")]
    prev = None
    for mes,sem,d in WEEKS:
        if mes != prev:
            r0.append(pp(mes, 7, True, BLANCO, TA_CENTER)); prev = mes
        else:
            r0.append(pp(""))
    r0 += [pp(""), pp(""), pp("")]

    r1 = [pp("Nº",7,True,BLANCO,TA_CENTER), pp("",6),
          pp("PROYECTO",7,True,BLANCO,TA_CENTER),
          pp("RESP.",7,True,BLANCO,TA_CENTER)]
    for i,(mes,sem,d) in enumerate(WEEKS):
        is_hoy = (i == HOY_IDX)
        r1.append(pp(sem, 6, is_hoy, NARANJA if is_hoy else BLANCO, TA_CENTER))
    r1 += [pp("NOTAS / ESTADO ACTUAL",6.5,True,BLANCO,TA_LEFT),
           pp("FIN EST.",6.5,True,BLANCO,TA_CENTER),
           pp("RIESGO",6.5,True,BLANCO,TA_CENTER)]
    return r0, r1

def build_style(data, dept_color):
    ts = TableStyle([
        ('FONTNAME',(0,0),(-1,-1),'Helvetica'),
        ('FONTSIZE',(0,0),(-1,-1),7),
        ('BACKGROUND',(0,0),(-1,0),dept_color),
        ('BACKGROUND',(0,1),(-1,1),colors.HexColor("#7A2844")),
        ('TEXTCOLOR',(0,0),(-1,1),BLANCO),
        ('ROWBACKGROUNDS',(0,2),(-1,-1),[BLANCO, PAPER]),
        ('GRID',(0,0),(-1,-1),0.15,colors.HexColor("#D0C8C0")),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,1),3), ('BOTTOMPADDING',(0,0),(-1,1),3),
        ('TOPPADDING',(0,2),(-1,-1),1), ('BOTTOMPADDING',(0,2),(-1,-1),1),
        ('LEFTPADDING',(0,0),(-1,-1),2), ('RIGHTPADDING',(0,0),(-1,-1),2),
    ])
    hoy_col = 4 + HOY_IDX  # 1-indexed: col 1=Nº, 2=FASE, 3=PROY, 4=RESP, 5..=semanas
    ts.add('BACKGROUND',(hoy_col-1,0),(hoy_col-1,-1), colors.HexColor("#FFF3E8"))
    ts.add('LINEAFTER', (hoy_col-1,0),(hoy_col-1,-1), 1.2, NARANJA)
    ts.add('LINEBEFORE',(hoy_col-1,0),(hoy_col-1,-1), 1.2, NARANJA)
    for bk in MONTH_BREAKS:
        mc = 4 + bk
        ts.add('LINEAFTER',(mc-1,0),(mc-1,-1), 1.8, GRANATE)
    # Merge meses row 0
    col, prev, start = 4, None, 4
    for i,(mes,sem,d) in enumerate(WEEKS):
        if mes != prev:
            if prev is not None: ts.add('SPAN',(start-1,0),(col-2,0))
            start, prev = col, mes
        col += 1
    ts.add('SPAN',(start-1,0),(col-2,0))
    # Franja de fase (col 2) + colorear celdas de Flowable
    for ri, row in enumerate(data):
        if ri < 2: continue
        cv2 = row[2] if len(row)>2 else None
        txt2 = cv2.text if hasattr(cv2,'text') else ""
        if txt2.strip().startswith("  ") and txt2.strip().isupper():
            ts.add('BACKGROUND',(0,ri),(-1,ri), colors.HexColor("#EEEAE5"))
            ts.add('LINEABOVE',(0,ri),(-1,ri), 0.5, GRIS_L)
            ts.add('SPAN',(0,ri),(-1,ri))
        if '🏖' in txt2 or 'VACACIONES' in txt2.upper():
            ts.add('BACKGROUND',(0,ri),(-1,ri), colors.HexColor("#2C4A2C"))
        if 'LATENTE' in txt2.upper() or 'PAUSADO' in txt2.upper():
            ts.add('BACKGROUND',(0,ri),(-1,ri), colors.HexColor("#EDEBE8"))
            ts.add('LINEABOVE',(0,ri),(-1,ri), 0.8, GRANATE)
            ts.add('SPAN',(0,ri),(-1,ri))
        # Franja de fase: primera actividad encontrada en la fila
        fase_col_color = None
        for ci in range(4, 4+N):
            if ci >= len(row): break
            cv = row[ci]
            if isinstance(cv, (ActCell, DiagCell)):
                fc = get_color(cv.act if hasattr(cv,'act') else cv.txt)
                if fc and not fase_col_color:
                    fase_col_color = fc
            elif isinstance(cv, HitoCell):
                fc = get_color(cv.txt)
                if fc and not fase_col_color:
                    fase_col_color = fc
        if fase_col_color:
            ts.add('BACKGROUND',(1,ri),(1,ri), fase_col_color)
    return ts

def gen_pdf(proyectos_activos, proyectos_latentes, fname, dept_color, dept_name):
    today = date.today()

    def hfn(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(dept_color)
        canvas.rect(0, H-14*mm, W, 14*mm, fill=1, stroke=0)
        canvas.setFillColor(BLANCO); canvas.setFont("Helvetica-Bold",12)
        canvas.drawString(8*mm, H-9*mm,
            f"ALEJANDRA POMBO DESIGN STUDIO  ·  PLANNING {dept_name.upper()}")
        canvas.setFont("Helvetica",8)
        canvas.setFillColor(colors.HexColor("#C26942"))
        canvas.drawRightString(W-8*mm, H-9*mm,
            f"{today.strftime('%d/%m/%Y')}  ·  Actualizado reunión equipo")
        canvas.setFillColor(NARANJA); canvas.rect(0,0,W,4*mm,fill=1,stroke=0)
        canvas.setFillColor(BLANCO); canvas.setFont("Helvetica",5.5)
        canvas.drawString(8*mm, 1.5*mm, "Planning interno · No distribuir")
        canvas.drawRightString(W-8*mm, 1.5*mm,
            f"APDS · {dept_name.upper()} · {today.strftime('%d/%m/%Y')}")
        canvas.restoreState()

    r0, r1 = make_headers(dept_color, dept_name)
    data = [r0, r1]

    for item in proyectos_activos:
        data.append(p_row(item))

    if proyectos_latentes:
        data.append(lat_row())
        for item in proyectos_latentes:
            data.append(p_row(item))

    # Alertas globales (idx=-1 → aparecen al pie)
    todas_alertas = []
    for item in proyectos_activos:
        for al in item.get('alertas_calculadas',[]):
            if isinstance(item,(list,tuple)) and len(item)==2:
                idx, txt = item
                if idx == -1:
                    todas_alertas.append(f"{proj['nombre']}: {txt}")

    _rh = []
    for i, row in enumerate(data):
        if i < 2: _rh.append(8*mm if i==0 else 9*mm); continue
        cv = row[2] if len(row)>2 else None
        txt = cv.text if hasattr(cv,'text') else ""
        if txt.strip().startswith("  ") or '🏖' in txt or 'LATENTE' in txt.upper():
            _rh.append(9*mm)
        else:
            _rh.append(CELL_H)

    t = Table(data, colWidths=COLS, rowHeights=_rh, repeatRows=2)
    t.setStyle(build_style(data, dept_color))

    story = [t]
    if todas_alertas:
        from reportlab.platypus import Spacer
        story.append(Spacer(1, 3*mm))
        for a in todas_alertas:
            story.append(Paragraph(f'● {a}',
                ParagraphStyle('a', fontName='Helvetica', fontSize=7,
                    textColor=GRIS_L, leading=9)))

    doc = SimpleDocTemplate(fname, pagesize=PAGE,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=16*mm, bottomMargin=8*mm)
    doc.build(story, onFirstPage=hfn, onLaterPages=hfn)
    print(f"✅ {fname}")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    suffix = HOY.strftime('%d%b').lower()
    wb = download_excel()
    master = read_master(wb)

    configs = [
        ('VIVIENDA',     GRANATE,                    'VIVIENDA'),
        ('RESTAURANTES', colors.HexColor("#8B3A00"), 'RESTAURANTES'),
        ('HOTELES',      colors.HexColor("#1A3A5C"), 'HOTELES'),
    ]

    for sheet, dept_color, dept_name in configs:
        gantt_dict, ordered = read_gantt_sheet(wb, sheet)
        # Enriquecer con master
        for item in ordered:
            k = item['nombre'].upper()
            mdata = master.get(k, {})
            for kk, vv in mdata.items():
                if vv and kk not in item:
                    item[kk] = vv
            if 'gantt' not in item:
                item['gantt'] = {}

        print(f"   {sheet}: {len(ordered)} proyectos en Gantt, {len(master)} en Master")
        proyectos = merge_capas(master, gantt_dict, ordered, dept_name)
        activos  = [x for x in proyectos if not x.get('is_latente') and not x.get('terminado')]
        latentes = [x for x in proyectos if x.get('is_latente') or x.get('terminado')]

        fname = f"/home/claude/planning_{dept_name[:4].lower()}_{suffix}.pdf"
        gen_pdf(activos, latentes, fname, dept_color, dept_name)

        n = sum(len(x.get('alertas_calculadas',[])) for x in activos)
        print(f"   → {len(activos)} activos, {len(latentes)} latentes, {n} alertas")
