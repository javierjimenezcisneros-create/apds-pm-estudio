"""
APDS gen_plan_v3.py — Planning departamental desde Excel
Arquitectura limpia según modelo aprobado 11 sep 2026

MODELO DE DATOS:
- Actividad (A): fase de duración ≥1 semana. Color de fondo.
- Hito (H): acontecimiento puntual (visita, reunión, FIN OBRA, etc.). 
            Una semana concreta.
- Celda con A+H: diagonal (triángulo sup-izq = A, inf-der = H).
- Prioridad: Gantt manual > retroplanning automático > fase actual.
- Falta de info: genera alerta en PDF, no bloquea generación.
"""
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Flowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import urllib.request, openpyxl, io, sys, os
from datetime import date

PAGE = landscape(A3)
W, H = float(PAGE[0]), float(PAGE[1])
MARGIN = 5*mm

# ── Paleta ────────────────────────────────────────────────────────────────────
GRANATE  = colors.HexColor("#5C1831")
NARANJA  = colors.HexColor("#C26942")
PAPER    = colors.HexColor("#F4F1EC")
PAPER2   = colors.HexColor("#EDE8E0")
BLANCO   = colors.white
GRIS     = colors.HexColor("#4A4A4A")
GRIS_L   = colors.HexColor("#9C9088")

# Actividades (fases de duración)
ACT_COLOR = {
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
}
# Hitos (acontecimiento puntual)
HITO_COLOR = {
    "FIN OBRA":  "#C62828",
    "ENTREGA":   "#5FAD5F",
    "APERTURA":  "#5FAD5F",
    "REUNIÓN":   "#A8D8A8",
    "VISITA":    "#A8D8A8",
    "ALEJANDRA": "#8B2252",
    "VIAJE":     "#8B2252",
    "REVISIÓN":  "#BDD7EE",
    "⚠":        "#FF4040",
}
# Texto blanco en fondos oscuros
TXT_BLANCO = {"FIN OBRA","ENTREGA","APERTURA","ALEJANDRA","VIAJE","PROY E","⚠"}

ALL_COLOR = {**ACT_COLOR, **HITO_COLOR}

def get_color(txt):
    if not txt: return None
    for k,v in ALL_COLOR.items():
        if k == txt.strip().upper() or k in txt.strip().upper():
            return colors.HexColor(v)
    return None

def is_hito(txt):
    return txt.strip().upper() in HITO_COLOR

def is_actividad(txt):
    return txt.strip().upper() in ACT_COLOR

# ── Celda diagonal A+H ────────────────────────────────────────────────────────
class DiagonalCell(Flowable):
    """
    Celda con diagonal: triángulo sup-izq = actividad, inf-der = hito.
    Max 2 elementos. Legible en A3.
    """
    def __init__(self, act_txt, hito_txt, cell_w, cell_h):
        super().__init__()
        self.act_txt  = act_txt.strip()
        self.hito_txt = hito_txt.strip()
        self.cell_w   = cell_w
        self.cell_h   = cell_h
        self.width    = cell_w
        self.height   = cell_h

    def draw(self):
        c = self.canv
        w, h = self.cell_w, self.cell_h
        ac = get_color(self.act_txt)  or colors.HexColor("#EEEEEE")
        hc = get_color(self.hito_txt) or colors.HexColor("#CCCCCC")

        # Triángulo superior-izquierda (actividad)
        c.setFillColor(ac)
        path = c.beginPath()
        path.moveTo(0, 0); path.lineTo(w, h); path.lineTo(0, h); path.close()
        c.drawPath(path, fill=1, stroke=0)

        # Triángulo inferior-derecha (hito)
        c.setFillColor(hc)
        path = c.beginPath()
        path.moveTo(0, 0); path.lineTo(w, 0); path.lineTo(w, h); path.close()
        c.drawPath(path, fill=1, stroke=0)

        # Línea diagonal
        c.setStrokeColor(colors.white)
        c.setLineWidth(0.8)
        c.line(0, 0, w, h)

        # Texto actividad (arriba izquierda)
        tc_act = colors.white if self.act_txt in TXT_BLANCO else colors.HexColor("#2A2A2A")
        c.setFillColor(tc_act)
        c.setFont("Helvetica-Bold", 5)
        short = self.act_txt[:6]
        c.drawString(1.5, h*0.65, short)

        # Texto hito (abajo derecha)
        tc_hit = colors.white if self.hito_txt in TXT_BLANCO else colors.HexColor("#2A2A2A")
        c.setFillColor(tc_hit)
        c.setFont("Helvetica-Bold", 5)
        short2 = self.hito_txt[:6]
        c.drawRightString(w-1.5, h*0.08, short2)

# ── Helper Paragraph ──────────────────────────────────────────────────────────
def p(text, size=7, bold=False, color=GRIS, align=TA_LEFT):
    fn = "Helvetica-Bold" if bold else "Helvetica"
    return Paragraph(str(text) if text else "",
        ParagraphStyle('_', fontName=fn, fontSize=size,
            textColor=color, leading=size*1.3, alignment=align))

# ── Semanas ───────────────────────────────────────────────────────────────────
WEEKS = [
    ("SEP","9 SEP"), ("SEP","14 SEP"), ("SEP","21 SEP"), ("SEP","28 SEP"),
    ("OCT","5 OCT"), ("OCT","12 OCT"), ("OCT","19 OCT"), ("OCT","26 OCT"),
    ("NOV","2 NOV"),
]
N = len(WEEKS)
HOY_IDX = 0
MONTH_BREAKS = [3, 7]  # SEP→OCT tras idx3, OCT→NOV tras idx7

WEEK_LABEL_TO_IDX = {sem: i for i,(mes,sem) in enumerate(WEEKS)}

# ── Columnas ──────────────────────────────────────────────────────────────────
COL_N  = 8*mm
COL_F  = 4*mm    # franja fase
COL_P  = 34*mm   # proyecto
COL_R  = 14*mm   # responsable
COL_NO = 56*mm   # notas
COL_FE = 11*mm
COL_RI = 14*mm
FIXED  = COL_N+COL_F+COL_P+COL_R+COL_NO+COL_FE+COL_RI
COL_W  = (W - 2*MARGIN - FIXED) / N
COL_SEM_START = 5  # 1-indexed

COLS = [COL_N, COL_F, COL_P, COL_R] + [COL_W]*N + [COL_NO, COL_FE, COL_RI]

# ── Construir celda semanal ───────────────────────────────────────────────────
def make_week_cell(txt):
    """
    txt puede ser:
      - "OBRA"            → actividad sola
      - "VISITA"          → hito solo
      - "OBRA|VISITA"     → actividad + hito → diagonal
      - ""                → vacía
    """
    if not txt or txt.strip() in ('None','—',''):
        return p("")
    
    parts = [t.strip() for t in txt.split('|')]
    
    if len(parts) == 2:
        act_t, hit_t = parts
        # Validar que tiene sentido
        if act_t and hit_t:
            return DiagonalCell(act_t, hit_t, COL_W, 7.5*mm)
    
    # Una sola entrada
    single = parts[0]
    bg = get_color(single)
    tc_str = "FFFFFF" if single in TXT_BLANCO else "4A4A4A"
    tc = colors.HexColor("#"+tc_str)
    return p(single, 6.5, True, tc, TA_CENTER)

# ── Fila de proyecto ──────────────────────────────────────────────────────────
def prow(num, nombre, equipo, semanas, fin_est="", riesgo="", nota="",
         alert=False, alertas_pm=None):
    """
    semanas: lista de N strings (puede tener "|" para dual)
    alertas_pm: lista de alertas acumuladas (se añaden aquí si procede)
    """
    nota_corta = nota[:72] + "…" if len(nota) > 72 else nota
    pc = colors.HexColor("#C0392B") if alert else GRANATE
    rc = {"ATENCIÓN ALTA":   colors.HexColor("#E07030"),
          "ATENCIÓN MÁXIMA": colors.HexColor("#C0392B"),
          "SEGUIMIENTO":     colors.HexColor("#1A5C1A"),
          "ESTABLE":         colors.HexColor("#1A5C1A"),
          "PARADO":          GRIS_L}.get(riesgo, GRIS)
    rshort = {"ATENCIÓN MÁXIMA":"AT.MÁX","ATENCIÓN ALTA":"AT.ALTA",
               "SEGUIMIENTO":"SEGUIM.","ESTABLE":"OK","PARADO":"PARADO"}.get(riesgo,riesgo[:7])

    row = [
        p(num,  6, False, GRIS_L, TA_CENTER),
        p("",   6),                          # franja fase — coloreada por style
        p(nombre, 8, True, pc),
        p(equipo, 6.5, False, GRIS),
    ]
    for i,(mes,sem) in enumerate(WEEKS):
        txt = semanas[i] if i < len(semanas) else ""
        row.append(make_week_cell(txt))
    row += [
        p(nota_corta, 6, False, GRIS),
        p(fin_est, 6.5, False, GRIS, TA_CENTER),
        p(rshort,  6,   True,  rc,   TA_CENTER),
    ]
    return row

def fase_sep(label):
    lbl   = p(f"  {label.upper()}", 6.5, True, colors.HexColor("#5C5248"), TA_LEFT)
    empty = p("")
    return [empty]*2 + [lbl] + [empty]*(N+3)

def latentes_sep():
    lbl   = p("  LATENTES / PAUSADOS", 6.5, True, GRIS_L, TA_LEFT)
    empty = p("")
    return [empty]*2 + [lbl] + [empty]*(N+3)

# ── Cabeceras ─────────────────────────────────────────────────────────────────
def make_headers(dept_color, dept_name):
    r0 = [p("",6), p(""), p("",7,True,BLANCO,TA_CENTER), p("")]
    prev = None
    for mes,sem in WEEKS:
        if mes != prev:
            r0.append(p(mes, 7, True, BLANCO, TA_CENTER))
            prev = mes
        else:
            r0.append(p(""))
    r0 += [p(""), p(""), p("")]

    r1 = [
        p("Nº",   7, True, BLANCO, TA_CENTER),
        p("",     6),
        p("PROYECTO", 7, True, BLANCO, TA_CENTER),
        p("RESP.",    7, True, BLANCO, TA_CENTER),
    ]
    for i,(mes,sem) in enumerate(WEEKS):
        is_hoy = (i == HOY_IDX)
        r1.append(p(sem, 6, is_hoy, NARANJA if is_hoy else BLANCO, TA_CENTER))
    r1 += [
        p("NOTAS / ESTADO ACTUAL", 6.5, True, BLANCO, TA_LEFT),
        p("FIN EST.", 6.5, True, BLANCO, TA_CENTER),
        p("RIESGO",   6.5, True, BLANCO, TA_CENTER),
    ]
    return r0, r1

# ── Table style ───────────────────────────────────────────────────────────────
def build_style(data, dept_color):
    ts = TableStyle([
        ('FONTNAME',  (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE',  (0,0), (-1,-1), 7),
        ('BACKGROUND',(0,0), (-1,0),  dept_color),
        ('BACKGROUND',(0,1), (-1,1),  colors.HexColor("#7A2844")),
        ('TEXTCOLOR', (0,0), (-1,1),  BLANCO),
        ('ROWBACKGROUNDS',(0,2),(-1,-1),[BLANCO, PAPER]),
        ('GRID',      (0,0), (-1,-1), 0.15, colors.HexColor("#D0C8C0")),
        ('VALIGN',    (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0), (-1,1),  3),
        ('BOTTOMPADDING', (0,0), (-1,1),  3),
        ('TOPPADDING',    (0,2), (-1,-1), 1.5),
        ('BOTTOMPADDING', (0,2), (-1,-1), 1.5),
        ('LEFTPADDING',   (0,0), (-1,-1), 2),
        ('RIGHTPADDING',  (0,0), (-1,-1), 2),
    ])

    # Semana HOY
    hoy_col = COL_SEM_START - 1 + HOY_IDX
    ts.add('BACKGROUND',(hoy_col,0),(hoy_col,-1), colors.HexColor("#FFF3E8"))
    ts.add('LINEAFTER', (hoy_col,0),(hoy_col,-1), 1.2, NARANJA)
    ts.add('LINEBEFORE',(hoy_col,0),(hoy_col,-1), 1.2, NARANJA)

    # Cambios de mes
    for bk in MONTH_BREAKS:
        mc = COL_SEM_START - 1 + bk
        ts.add('LINEAFTER',(mc,0),(mc,-1), 1.8, GRANATE)

    # Merge meses (row 0)
    col, prev, start = COL_SEM_START-1, None, COL_SEM_START-1
    for i,(mes,sem) in enumerate(WEEKS):
        if mes != prev:
            if prev is not None:
                ts.add('SPAN',(start,0),(col-1,0))
            start, prev = col, mes
        col += 1
    ts.add('SPAN',(start,0),(col-1,0))

    # Colorear celdas y franja de fase
    for ri, row in enumerate(data):
        if ri < 2: continue
        # Franja de fase: primer color de actividad encontrado en la fila
        fase_col = None
        for ci in range(COL_SEM_START-1, COL_SEM_START-1+N):
            cv = row[ci] if ci < len(row) else None
            if cv is None: continue
            if isinstance(cv, DiagonalCell):
                bg = get_color(cv.act_txt)
                if bg: ts.add('BACKGROUND',(ci,ri),(ci,ri), BLANCO)  # diagonal draws itself
                if not fase_col and bg: fase_col = bg
            elif hasattr(cv,'text') and cv.text:
                bg = get_color(cv.text)
                if bg:
                    ts.add('BACKGROUND',(ci,ri),(ci,ri), bg)
                    if not fase_col: fase_col = bg
        if fase_col:
            ts.add('BACKGROUND',(1,ri),(1,ri), fase_col)

        # Separadores de fase
        cv2 = row[2] if len(row)>2 else None
        txt2 = cv2.text if hasattr(cv2,'text') else ""
        if txt2 and txt2.strip().startswith("  ") and txt2.strip().isupper():
            ts.add('BACKGROUND',(0,ri),(-1,ri), colors.HexColor("#EEEAE5"))
            ts.add('LINEABOVE', (0,ri),(-1,ri), 0.5, GRIS_L)
            ts.add('SPAN',(0,ri),(-1,ri))
        if '🏖' in txt2 or 'VACACIONES' in txt2.upper():
            ts.add('BACKGROUND',(0,ri),(-1,ri), colors.HexColor("#2C4A2C"))
        if 'LATENTE' in txt2.upper() or 'PAUSADO' in txt2.upper():
            ts.add('BACKGROUND',(0,ri),(-1,ri), colors.HexColor("#EDEBE8"))
            ts.add('LINEABOVE', (0,ri),(-1,ri), 0.8, GRANATE)
            ts.add('SPAN',(0,ri),(-1,ri))
    return ts

# ── Gen PDF ───────────────────────────────────────────────────────────────────
def gen_pdf(data, fname, dept_color, dept_name, alertas_pm=None):
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
            f"{today.strftime('%d %B %Y')}  ·  Actualizado reunión equipo")
        canvas.setFillColor(NARANJA)
        canvas.rect(0, 0, W, 4*mm, fill=1, stroke=0)
        canvas.setFillColor(BLANCO); canvas.setFont("Helvetica",5.5)
        canvas.drawString(8*mm, 1.5*mm, "Planning interno · No distribuir")
        canvas.drawRightString(W-8*mm, 1.5*mm,
            f"APDS · {dept_name.upper()} · {today.strftime('%d/%m/%Y')}")
        canvas.restoreState()

    # Row heights
    _rh = []
    for i, row in enumerate(data):
        if i < 2: _rh.append(8*mm if i==0 else 9*mm); continue
        cv = row[2] if len(row)>2 else None
        txt = cv.text if hasattr(cv,'text') else ""
        if txt.strip().startswith("  ") or '🏖' in txt or 'LATENTE' in txt.upper():
            _rh.append(9*mm)
        else:
            _rh.append(7.5*mm)

    t = Table(data, colWidths=COLS, rowHeights=_rh, repeatRows=2)
    t.setStyle(build_style(data, dept_color))

    story = [t]

    # Alertas del PM al pie
    if alertas_pm:
        from reportlab.platypus import Spacer
        story.append(Spacer(1, 3*mm))
        for alerta in alertas_pm:
            story.append(Paragraph(f"⚠ {alerta}",
                ParagraphStyle('a', fontName='Helvetica', fontSize=7,
                    textColor=colors.HexColor("#B86328"), leading=9)))

    doc = SimpleDocTemplate(fname, pagesize=PAGE,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=16*mm, bottomMargin=8*mm)
    doc.build(story, onFirstPage=hfn, onLaterPages=hfn)
    print(f"✅ {fname}")

# ══════════════════════════════════════════════════════════════════════════════
# LECTOR DE EXCEL
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
        local = EXCEL
        if os.path.exists(local):
            print(f"⚠ Sin red — usando {local} local")
            return openpyxl.load_workbook(local, data_only=True)
        print(f"❌ {e}"); sys.exit(1)

def parse_cell(raw):
    """
    Convierte el valor de una celda Excel en el string para make_week_cell().
    El PM puede escribir:
      - "OBRA"          → actividad
      - "VISITA"        → hito
      - "OBRA|VISITA"   → dual (diagonal)
    """
    if raw is None: return ""
    v = str(raw).strip()
    if v in ('None','—',''): return ""
    return v

def fill_between(semanas):
    """
    Rellena celdas vacías ENTRE dos celdas con la misma actividad.
    NO propaga más allá del último dato explícito.
    Las celdas con hito no se rellenan (pueden convivir vía |).
    """
    # Encontrar rangos de actividad
    last_act = None
    last_act_idx = -1

    for i in range(N):
        raw = semanas[i]
        if not raw:
            continue
        # Extraer componente de actividad (puede ser "OBRA", "OBRA|VISITA", etc.)
        parts = raw.split('|')
        act_part = parts[0] if is_actividad(parts[0]) else None
        
        if act_part:
            if act_part == last_act and last_act_idx >= 0:
                # Rellenar vacíos entre last_act_idx y i con la misma actividad
                for j in range(last_act_idx+1, i):
                    if not semanas[j]:
                        semanas[j] = act_part
                    elif '|' not in semanas[j] and is_hito(semanas[j]):
                        # Combinar: actividad existente + hito ya presente → diagonal
                        semanas[j] = f"{act_part}|{semanas[j]}"
            last_act = act_part
            last_act_idx = i

    return semanas

def check_retroplanning(nombre, semanas, fin_est, alertas):
    """
    Verifica retroplanning básico y añade alertas si falta info.
    NO modifica semanas (Gantt manual tiene prioridad).
    Solo alerta.
    """
    # Detectar MONTAJE o ENTREGA en el Gantt
    hitos = [(i,v) for i,v in enumerate(semanas) 
             if v and any(h in v.upper() for h in ('MONTAJE','ENTREGA','APERTURA','FIN OBRA'))]
    
    if not hitos and fin_est and fin_est not in ('—','','2027','2026','Pdte'):
        alertas.append(f"{nombre}: fecha fin '{fin_est}' conocida pero sin hito de cierre en el Gantt")

    if hitos:
        idx_hito, _ = hitos[0]
        # Verificar que hay PEDIDOS al menos 3 semanas antes
        has_pedidos = any('PEDIDO' in str(v).upper() for v in semanas[:idx_hito] if v)
        if not has_pedidos and idx_hito >= 2:
            alertas.append(f"{nombre}: ⚠ PEDIDOS no identificados antes de {WEEKS[idx_hito][1]}")

def excel_to_data(ws, dept_color, dept_name):
    """Lee una hoja de planning del Excel y construye data[] para gen_pdf()."""
    rows = list(ws.iter_rows(values_only=True))
    
    # Encontrar cabecera y columnas de semana
    header_idx = None
    week_cols  = {}  # col_idx(0-based) → week_label
    
    for i, row in enumerate(rows):
        if len(row) > 1 and str(row[1] or '').strip() == 'PROYECTO':
            header_idx = i
            for j in range(6, len(row)):
                v = row[j]
                if v and isinstance(v, str) and any(c.isdigit() for c in str(v)):
                    week_cols[j] = str(v).strip()
            break
    
    if header_idx is None:
        print(f"   ⚠ Sin cabecera en {ws.title}")
        return None, []

    alertas_pm = []
    r0, r1 = make_headers(dept_color, dept_name)
    data = [r0, r1]

    for row in rows[header_idx+1:]:
        if not row: continue
        col0 = str(row[0] or '').strip()
        col1 = str(row[1] or '').strip()
        col2 = str(row[2] or '').strip()
        col3 = str(row[3] or '').strip()
        col4 = str(row[4] or '').strip()
        col5 = str(row[5] or '').strip()

        if not col1 and not col0: continue

        # Separador de fase
        if col2 and col2.isupper() and not col0 and not col5:
            data.append(fase_sep(col2.strip()))
            continue

        # Vacaciones
        if '🏖' in col1 or 'VACACIONES' in col1.upper():
            vr = [p("🏖",7,True,BLANCO,TA_CENTER), p(""),
                  p("VACACIONES",6.5,True,BLANCO), p("")]
            for i,(mes,sem) in enumerate(WEEKS):
                wlabel_match = week_cols.get(next((c for c,l in week_cols.items() if l==sem), -1))
                vr.append(p("", 7, False, BLANCO, TA_CENTER))
            vr += [p(""), p(""), p("")]
            data.append(vr)
            continue

        # Latentes
        if 'LATENTE' in col2.upper() or 'PAUSADO' in col2.upper():
            data.append(latentes_sep())
            continue

        if not col1 or len(col1) < 2: continue

        # Construir semanas desde el Gantt del Excel
        semanas = [''] * N
        for j, wlabel in week_cols.items():
            idx = WEEK_LABEL_TO_IDX.get(wlabel, -1)
            if idx < 0: continue
            if j < len(row) and row[j] is not None:
                v = parse_cell(row[j])
                if v:
                    semanas[idx] = v  # Gantt manual — prioridad absoluta

        # fill_between: rellenar vacíos entre actividades explícitas
        semanas = fill_between(semanas)

        # Verificar retroplanning (solo alertas)
        check_retroplanning(col1, semanas, col4, alertas_pm)

        alert = '⚠' in col3 or col5 == 'ATENCIÓN MÁXIMA'
        data.append(prow(
            num     = col0,
            nombre  = col1,
            equipo  = col2,
            semanas = semanas,
            fin_est = col4,
            riesgo  = col5 or 'SEGUIMIENTO',
            nota    = col3,
            alert   = alert,
        ))

    return data, alertas_pm

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    suffix = date.today().strftime('%d%b').lower().replace('sep','sep').replace('oct','oct')
    
    wb = download_excel()

    configs = [
        ('VIVIENDA',     GRANATE,                        'VIVIENDA'),
        ('RESTAURANTES', colors.HexColor("#8B3A00"),     'RESTAURANTES'),
        ('HOTELES',      colors.HexColor("#1A3A5C"),     'HOTELES'),
    ]

    for sheet_name, dept_color, dept_name in configs:
        if sheet_name not in wb.sheetnames:
            print(f"⚠ Hoja {sheet_name} no encontrada")
            continue
        ws = wb[sheet_name]
        data, alertas = excel_to_data(ws, dept_color, dept_name)
        if data and len(data) > 2:
            fname = f"/home/claude/planning_{sheet_name.lower()[:4]}_{suffix}.pdf"
            gen_pdf(data, fname, dept_color, dept_name, alertas)
            if alertas:
                print(f"   {len(alertas)} alertas PM en {dept_name}")
        else:
            print(f"⚠ Sin datos en {sheet_name}")
