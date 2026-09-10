from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

PAGE = landscape(A3)
W = float(PAGE[0])
H = float(PAGE[1])
MARGIN = 5*mm

# ── Paleta ────────────────────────────────────────────────────────────────────
GRANATE = colors.HexColor("#5C1831")
NARANJA = colors.HexColor("#C26942")
PAPER   = colors.HexColor("#F4F1EC")
PAPER2  = colors.HexColor("#EDE8E0")
BLANCO  = colors.white
GRIS    = colors.HexColor("#4A4A4A")
GRIS_L  = colors.HexColor("#9C9088")

# ── Colores de actividad ──────────────────────────────────────────────────────
ACT = {
    "PROY B":    colors.HexColor("#BDD7EE"),
    "PROY E":    colors.HexColor("#70B0D8"),
    "PROY DECO": colors.HexColor("#C9B8E8"),
    "ANT.PROY":  colors.HexColor("#D4C4F0"),
    "OBRA":      colors.HexColor("#E8924A"),
    "FIN OBRA":  colors.HexColor("#C62828"),
    "PEDIDOS":   colors.HexColor("#FFE384"),
    "MONTAJE":   colors.HexColor("#E87878"),
    "REUNIÓN":   colors.HexColor("#A8D8A8"),
    "VISITA":    colors.HexColor("#A8D8A8"),
    "ENTREGA":   colors.HexColor("#5FAD5F"),
    "REMATES":   colors.HexColor("#F5DE7A"),
    "RENDERS":   colors.HexColor("#C8C8C8"),
    "ALEJANDRA": colors.HexColor("#8B2252"),
    "VIAJE":     colors.HexColor("#8B2252"),
    "PDTE LIC":  colors.HexColor("#D0CEC8"),
    "FUERA":     colors.HexColor("#888888"),
    "⚠":        colors.HexColor("#FF4040"),
}
TXT_BLANCO = {"FIN OBRA","ENTREGA","ALEJANDRA","VIAJE","FUERA","PROY E","⚠"}

def act_bg(txt):
    if not txt: return None
    for k,v in ACT.items():
        if k in str(txt).upper(): return v
    return None

def p(text, size=7, bold=False, color=GRIS, align=TA_LEFT):
    fn = "Helvetica-Bold" if bold else "Helvetica"
    return Paragraph(str(text) if text else "",
        ParagraphStyle('_', fontName=fn, fontSize=size,
            textColor=color, leading=size*1.3, alignment=align))

# ── Semanas ───────────────────────────────────────────────────────────────────
# idx: 0=7SEP(HOY) 1=14SEP 2=21SEP 3=28SEP | 4=5OCT 5=12OCT 6=19OCT 7=26OCT | 8=2NOV 9=9NOV 10=16NOV
WEEKS = [
    ("SEP","9 SEP"), ("SEP","14 SEP"), ("SEP","21 SEP"), ("SEP","28 SEP"),
    ("OCT","5 OCT"), ("OCT","12 OCT"), ("OCT","19 OCT"), ("OCT","26 OCT"),
    ("NOV","2 NOV"),
]
N = len(WEEKS)
HOY = 0  # idx semana actual

# Cambios de mes (columna del último día del mes anterior)
# SEP→OCT: después de idx3 (28SEP) → col_sem_start+3
# OCT→NOV: después de idx7 (26OCT) → col_sem_start+7
MONTH_BREAKS = [3, 7]  # después de estos idx hay cambio de mes

def ws(s0="",s1="",s2="",s3="",s4="",s5="",s6="",s7="",s8="",s9="",s10=""):
    return [s0,s1,s2,s3,s4,s5,s6,s7,s8,s9,s10]

# ── Columnas ──────────────────────────────────────────────────────────────────
COL_N  = 8*mm    # Nº
COL_F  = 4*mm    # indicador fase (franja color)
COL_P  = 34*mm   # proyecto
COL_R  = 14*mm   # responsable
COL_NO = 56*mm   # notas — ancho para que el texto quepa
COL_FE = 11*mm   # fin est
COL_RI = 14*mm   # riesgo

FIXED = COL_N + COL_F + COL_P + COL_R + COL_NO + COL_FE + COL_RI
COL_W = (W - 2*MARGIN - FIXED) / N   # ≈13mm por semana

COL_SEM_START = 5  # columna donde empiezan las semanas (1-indexed)
COLS = [COL_N, COL_F, COL_P, COL_R] + [COL_W]*N + [COL_NO, COL_FE, COL_RI]

# ── Header canvas ─────────────────────────────────────────────────────────────
def header_fn(canvas, doc, dept_color):
    canvas.saveState()
    canvas.setFillColor(dept_color)
    canvas.rect(0, H-14*mm, W, 14*mm, fill=1, stroke=0)
    canvas.setFillColor(BLANCO)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(8*mm, H-9*mm, "ALEJANDRA POMBO DESIGN STUDIO  ·  PLANNING VIVIENDA")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#C26942"))
    canvas.drawRightString(W-8*mm, H-9*mm, "9 septiembre 2026  ·  Actualizado reunión equipo")
    canvas.setFillColor(NARANJA)
    canvas.rect(0, 0, W, 4*mm, fill=1, stroke=0)
    canvas.setFillColor(BLANCO)
    canvas.setFont("Helvetica", 5.5)
    canvas.drawString(8*mm, 1.5*mm, "Planning interno · No distribuir")
    canvas.drawRightString(W-8*mm, 1.5*mm, "APDS · VIVIENDA · 09/09/2026")
    canvas.restoreState()

def hfn(c,d): header_fn(c, d, GRANATE)

# ── Build table style ─────────────────────────────────────────────────────────
def build_style(data, dept_color):
    ts = TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('BACKGROUND', (0,0), (-1,0), dept_color),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor("#7A2844")),
        ('TEXTCOLOR', (0,0), (-1,1), BLANCO),
        ('ROWBACKGROUNDS', (0,2), (-1,-1), [BLANCO, PAPER]),
        ('GRID', (0,0), (-1,-1), 0.15, colors.HexColor("#D0C8C0")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,1), 3),
        ('BOTTOMPADDING', (0,0), (-1,1), 3),
        ('TOPPADDING', (0,2), (-1,-1), 1.5),
        ('BOTTOMPADDING', (0,2), (-1,-1), 1.5),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
    ])

    # Semana actual — fondo destacado
    HOY_COL = COL_SEM_START - 1 + HOY  # 0-indexed
    ts.add('BACKGROUND', (HOY_COL,0), (HOY_COL,-1), colors.HexColor("#FFF3E8"))
    ts.add('LINEAFTER',  (HOY_COL,0), (HOY_COL,-1), 1.2, NARANJA)
    ts.add('LINEBEFORE', (HOY_COL,0), (HOY_COL,-1), 1.2, NARANJA)

    # Líneas de cambio de mes (verticales, granate)
    for break_idx in MONTH_BREAKS:
        col = COL_SEM_START - 1 + break_idx  # 0-indexed
        ts.add('LINEAFTER', (col,0), (col,-1), 1.8, GRANATE)

    # Merge meses (row 0)
    col = COL_SEM_START - 1  # 0-indexed start of weeks
    prev_mes = None
    start = col
    for i,(mes,sem) in enumerate(WEEKS):
        if mes != prev_mes:
            if prev_mes is not None:
                ts.add('SPAN', (start,0), (col-1,0))
            start = col
            prev_mes = mes
        col += 1
    ts.add('SPAN', (start,0), (col-1,0))

    # Colorear celdas de actividad
    for ri, row in enumerate(data):
        if ri < 2: continue
        for ci in range(COL_SEM_START-1, COL_SEM_START-1+N):
            cv = row[ci]
            txt = cv.text if hasattr(cv,'text') else str(cv) if cv else ""
            bg = act_bg(txt)
            if bg:
                ts.add('BACKGROUND', (ci,ri), (ci,ri), bg)
            # Franja fase (col 1 = COL_F) — color del primer hito no vacío
            if ci == COL_SEM_START-1 and bg:
                ts.add('BACKGROUND', (1,ri), (1,ri), bg)

        # Detectar color de franja de fase desde cualquier semana
        for ci in range(COL_SEM_START-1, COL_SEM_START-1+N):
            cv = row[ci]
            txt = cv.text if hasattr(cv,'text') else str(cv) if cv else ""
            bg = act_bg(txt)
            if bg:
                ts.add('BACKGROUND', (1,ri), (1,ri), bg)
                break

        # Separadores de fase
        cv0 = row[2] if len(row)>2 else None
        txt0 = cv0.text if hasattr(cv0,'text') else str(cv0) if cv0 else ""
        if txt0 and txt0.startswith("  ") and txt0.strip().isupper():
            ts.add('BACKGROUND', (0,ri), (-1,ri), colors.HexColor("#EEEAE5"))
            ts.add('LINEABOVE', (0,ri), (-1,ri), 0.5, GRIS_L)
            ts.add('SPAN', (0,ri), (-1,ri))
        # Vacaciones
        if '🏖' in txt0 or 'VACACIONES' in txt0:
            ts.add('BACKGROUND', (0,ri), (-1,ri), colors.HexColor("#2C4A2C"))
        # Latentes
        if 'LATENTES' in txt0 or 'PAUSADOS' in txt0:
            ts.add('BACKGROUND', (0,ri), (-1,ri), colors.HexColor("#EDEBE8"))
            ts.add('LINEABOVE', (0,ri), (-1,ri), 0.8, GRANATE)
            ts.add('SPAN', (0,ri), (-1,ri))

    return ts

# ── Fila de proyecto ──────────────────────────────────────────────────────────
def prow(num, nombre, equipo, semanas, fin_est="", riesgo="", nota="", alert=False):
    pc = colors.HexColor("#C0392B") if alert else GRANATE
    rc = {"ATENCIÓN ALTA": colors.HexColor("#E07030"),
          "ATENCIÓN MÁXIMA": colors.HexColor("#C0392B"),
          "SEGUIMIENTO": colors.HexColor("#1A5C1A"),
          "ESTABLE": colors.HexColor("#1A5C1A"),
          "PARADO": GRIS_L}.get(riesgo, GRIS)
    rshort = {"ATENCIÓN MÁXIMA":"AT.MÁX","ATENCIÓN ALTA":"AT.ALTA",
               "SEGUIMIENTO":"SEGUIM.","ESTABLE":"OK","PARADO":"PARADO"}.get(riesgo, riesgo[:7])

    # Truncar nota a máximo que quepa en 56mm a 6.5pt (~70 chars)
    nota70 = nota[:72] + "…" if len(nota) > 72 else nota

    row = [
        p(num, 6, False, GRIS_L, TA_CENTER),
        p("", 6),  # franja fase — coloreada por build_style
        p(nombre, 8, True, pc),
        p(equipo, 6.5, False, GRIS),
    ]
    for i,(mes,sem) in enumerate(WEEKS):
        txt = semanas[i] if i < len(semanas) else ""
        tc = BLANCO if txt in TXT_BLANCO else GRIS
        row.append(p(txt, 6.5, bool(txt), tc, TA_CENTER))
    row.append(p(nota70, 6, False, GRIS))
    row.append(p(fin_est, 6.5, False, GRIS, TA_CENTER))
    row.append(p(rshort, 6, True, rc, TA_CENTER))
    return row

def fase_sep(label):
    lbl = p(f"  {label.upper()}", 6.5, True, colors.HexColor("#5C5248"), TA_LEFT)
    empty = p("")
    return [empty]*2 + [lbl] + [empty]*(N+3)

def latentes_sep():
    lbl = p("  LATENTES / PAUSADOS", 6.5, True, GRIS_L, TA_LEFT)
    empty = p("")
    return [empty]*2 + [lbl] + [empty]*(N+3)

def gen_pdf(data, fname, dept_color):
    _rh = [8*mm, 9*mm]
    for i, row in enumerate(data):
        if i < 2:
            continue
        cv = row[2] if len(row) > 2 else None
        txt = cv.text if hasattr(cv,'text') else ""
        if txt and (txt.startswith("  ") or "🏖" in txt):
            _rh.append(9*mm)   # separador
        elif "LATENTES" in txt or "PAUSADOS" in txt:
            _rh.append(9*mm)
        else:
            _rh.append(7.5*mm)  # datos — altura compacta

    t = Table(data, colWidths=COLS, rowHeights=_rh, repeatRows=2)
    t.setStyle(build_style(data, dept_color))

    def hfn(c,d): header_fn(c,d,dept_color)

    doc = SimpleDocTemplate(fname, pagesize=PAGE,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=16*mm, bottomMargin=6*mm)
    doc.build([t], onFirstPage=hfn, onLaterPages=hfn)
    print(f"✅ {fname}")

# ── Header rows ───────────────────────────────────────────────────────────────
def make_headers(dept_color):
    # Row 0: meses
    r0 = [p("",6), p(""), p("", 7, True, BLANCO, TA_CENTER), p("")]
    prev_mes = None
    for mes,sem in WEEKS:
        if mes != prev_mes:
            r0.append(p(mes, 7, True, BLANCO, TA_CENTER))
            prev_mes = mes
        else:
            r0.append(p(""))
    r0 += [p(""), p(""), p("")]

    # Row 1: columnas
    r1 = [
        p("Nº",7,True,BLANCO,TA_CENTER),
        p("",6),
        p("PROYECTO",7,True,BLANCO,TA_CENTER),
        p("RESP.",7,True,BLANCO,TA_CENTER),
    ]
    for mes,sem in WEEKS:
        is_hoy = (WEEKS.index((mes,sem)) == HOY)
        r1.append(p(sem, 6, is_hoy, NARANJA if is_hoy else BLANCO, TA_CENTER))
    r1 += [
        p("NOTAS / ESTADO ACTUAL", 6.5, True, BLANCO, TA_LEFT),
        p("FIN EST.", 6.5, True, BLANCO, TA_CENTER),
        p("RIESGO", 6.5, True, BLANCO, TA_CENTER),
    ]
    return r0, r1

# ══════════════════════════════════════════════════════════════════════════════
# DATOS VIVIENDA — 7 sep 2026 (LIMPIO)
# idx: 0=7SEP(HOY) 1=14SEP 2=21SEP 3=28SEP 4=5OCT 5=12OCT 6=19OCT 7=26OCT 8=2NOV 9=9NOV 10=16NOV
# ══════════════════════════════════════════════════════════════════════════════
r0, r1 = make_headers(GRANATE)
data = [r0, r1]

# ── REMATES / ENTREGA ─────────────────────────────────────────────────────────
data.append(fase_sep("REMATES / ENTREGA"))
data += [
    prow("241","VALENCIA","Sara/Andrea",
         ws("REMATES","REMATES","REMATES","REMATES"),
         "Sep'26","SEGUIMIENTO",
         nota="Remates en ejecución hasta fin sep. Solicitar planos producción. Terraza pdte cliente."),
    prow("224","PEDRAZA","Olatz/Paula",
         ws("REMATES","REMATES"),
         "Oct'26","SEGUIMIENTO",
         nota="Remates obra. Falta paisajismo y piscina. Fase 2: cuadras+casa jueces — planificar."),
    prow("267","CAMINO SUR 70","Cristina/Nela",
         ws("OBRA","REMATES","REMATES"),
         "Oct'26","SEGUIMIENTO",
         nota="Terminar vie+sáb luminarias. Semana que viene remates y cosas pendientes."),
    prow("","ABUBILLA","Paula",
         ws("REMATES","FIN OBRA"),
         "Sep'26","SEGUIMIENTO",
         nota="Terminar semana que viene. Sofá y cortinas."),
]

# ── FIN DE OBRA ───────────────────────────────────────────────────────────────
data.append(fase_sep("FIN DE OBRA"))
data += [
    prow("223","ALCALÁ 58","Alicia/Javi",
         ws("OBRA","OBRA","OBRA","FIN OBRA"),
         "Sep'26","SEGUIMIENTO",
         nota="Termina última semana septiembre. Fin del proyecto."),
    prow("264","LA FLORIDA","Paula",
         ws("OBRA","FIN OBRA","REMATES","REMATES"),
         "Sep'26","SEGUIMIENTO",
         nota="Mudanza clientes finales sep. Remates hasta fin de mes."),
]

# ── PROYECTO DECORACIÓN (antes que Obra) ──────────────────────────────────────
data.append(fase_sep("PROYECTO DECORACIÓN"))
data += [
    prow("275","PASEO LAGOS 121","Olatz",
         ws("REUNIÓN","PROY DECO","PROY DECO","PEDIDOS","PEDIDOS"),
         "Ene'27","ATENCIÓN ALTA",
         nota="⚠ Reunión viernes. HITO: deco cerrado sep · presupuesto sem 28sep · pedidos oct · entrega ene.",
         alert=True),
    prow("232","VIV PALOMA RD","Olatz/Andrea",
         ws("PROY DECO","PROY DECO"),
         "Jul'27","SEGUIMIENTO",
         nota="Olatz con cambios clientes esta semana. Se compagina con obra. Reunión sep."),
]

# ── OBRA EN EJECUCIÓN ─────────────────────────────────────────────────────────
data.append(fase_sep("OBRA EN EJECUCIÓN"))
data += [
    prow("254","LA RINCONADA","Cristina/Nela",
         ws("OBRA","OBRA","OBRA","OBRA","OBRA","OBRA","OBRA","FIN OBRA","ENTREGA"),
         "Nov'26","ATENCIÓN ALTA",
         nota="Deco muy bien. Obra lenta — pedir planning. FIN OBRA finales oct. Entrega nov. ⚠ ¿Pedidos deco realizados?",
         
         alert=True),
    prow("271","VIUDA DE ALDAMA 3","Nela/Andrea",
         ws("","OBRA","OBRA","OBRA","OBRA","OBRA","PROY DECO","OBRA","OBRA","OBRA","OBRA"),
         "26 feb'27","ATENCIÓN ALTA",
         nota="⚠ HITO 19 oct: cerrar proy deco para fabricación. Montaje 11 ene. Parón nav. Entrega 26 feb.",
         alert=True),
    prow("268","MONTESQUINZA","Sara",
         ws(),
         "2027","ATENCIÓN ALTA",
         nota="Parado por consulta urbanística especial. Sin fecha de reanudación.",
         alert=True),
    prow("265","PESQUERA","Paula",
         ws("OBRA","OBRA","OBRA","OBRA","OBRA","OBRA","OBRA","OBRA","OBRA","OBRA","OBRA"),
         "Ene'27","SEGUIMIENTO",
         nota="Proyecto obra entregado. Terminar enero. Constructora en marcha."),
    prow("216","SANTANDER VIV","Sara",
         ws("","VISITA","PROY DECO","PROY DECO","PEDIDOS","PEDIDOS","PEDIDOS","PEDIDOS"),
         "Dic'26","ATENCIÓN ALTA",
         nota="⚠ Retroplanning: deco cerrar oct · pedidos oct/nov · montaje dic. Organizar visita sem que viene."),
    prow("242","IBIZA","Sara",
         ws("","OBRA","PROY DECO","PROY DECO","PEDIDOS","PEDIDOS","PEDIDOS","PEDIDOS"),
         "Dic'26","ATENCIÓN ALTA",
         nota="⚠ Retroplanning: inicio 15 sep · deco desde oct · pedidos oct/nov · montaje dic. PM local planifica."),
]

# ── PROYECTO EJECUCIÓN / DECO + OBRA ─────────────────────────────────────────
data.append(fase_sep("PROYECTO EJECUCIÓN / DECO"))
data += [
    prow("255","PASEO LAGOS 105","Sara/Andrea",
         ws("","REUNIÓN","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E"),
         "Ene'27(obra)","ATENCIÓN ALTA",
         nota="Proyecto de ejecución. Reunión 15 sep. Andrea con renders. Deco arranca cuando empiece obra ene.",
         alert=True),
    prow("239","TORRE VALENCIA","Paula",
         ws("","","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E"),
         "2027","SEGUIMIENTO",
         nota="Replanteo iluminación. Cliente sin decisiones domótica. Sin novedades."),
]

# ── RENDERS / PROYECTO BÁSICO ─────────────────────────────────────────────────
data.append(fase_sep("RENDERS / PROYECTO BÁSICO"))
data += [
    prow("211","CAMINO SUR 35","Nela",
         ws("RENDERS","RENDERS","RENDERS","RENDERS","RENDERS","RENDERS","RENDERS","RENDERS","RENDERS","RENDERS","RENDERS"),
         "2027","SEGUIMIENTO",
         nota="Esta semana: enviar calendario renders por zonas al cliente."),
]

# ── PENDIENTE / NUEVOS ────────────────────────────────────────────────────────
data.append(fase_sep("PENDIENTE / NUEVOS"))
data += [
    prow("273","VIUDA DE ALDAMA 2","Sin asignar",
         ws(),
         "2027","SEGUIMIENTO",
         nota="Organizar primera reunión primeros de octubre."),
    prow("258","HERMOSILLA","Nela/Olatz",
         ws(),
         "Mar'27","SEGUIMIENTO",
         nota="Cliente no contesta. Seguimiento activo. Tenía precio constructora."),
    prow("262","TEPEYAC","Paula",
         ws("REUNIÓN"),
         "2027","SEGUIMIENTO",
         nota="Reunión miércoles 10 sep con Raúl (online). Cerrar proyecto y organizar obra."),
    prow("","ANTIC COLONIAL","Sin asignar",
         ws(),
         "2026","SEGUIMIENTO",
         nota="Colaboración con marca azulejos. Ver con Sara en qué punto está."),
    prow("","PORTAL DE FERRAZ 78","Sin asignar",
         ws(),
         "2026","SEGUIMIENTO",
         nota="Reforma portal oficina. Sin novedades."),
    prow("231","GAMAL STO. DOMINGO","Sofía/Olatz",
         ws("","","ALEJANDRA"),
         "—","SEGUIMIENTO",
         nota="Obra terminada. Ale va lun 21 sep a revisar y ver nuevas obras. NUEVA OBRA: Gamal La Romana."),
    prow("","GAMAL LA ROMANA","Sin asignar",
         ws(),
         "2027","SEGUIMIENTO",
         nota="Nuevo proyecto. Ale abre puerta en visita 21 sep."),
    prow("","CONDE ORGAZ","Sin asignar",
         ws(),
         "—","SEGUIMIENTO",
         nota="Lead. Posible proyecto vivienda. Clientes van a llamar."),
]

# ── LATENTES ──────────────────────────────────────────────────────────────────
data.append(latentes_sep())
data += [
    prow("225","ANA HONTANAR","Paula",ws(),"—","PARADO","Después de verano."),
    prow("","HABITACIÓN ABI","Andrea",ws(),"—","PARADO","Pdte feedback presupuesto."),
    prow("","MONTALBÁN","Olatz",ws(),"—","PARADO","—"),
    prow("265","JAIME PESQUERA","Paula",ws(),"—","PARADO","Después de verano."),
]

gen_pdf(data, "/home/claude/planning_viv_9sep.pdf", GRANATE)

# ══════════════════════════════════════════════════════════════════════════════
# RESTAURANTES — 7 sep 2026
# ══════════════════════════════════════════════════════════════════════════════
def hfn_rest(c,d): 
    c.saveState()
    c.setFillColor(colors.HexColor("#8B3A00"))
    c.rect(0, H-14*mm, W, 14*mm, fill=1, stroke=0)
    c.setFillColor(BLANCO); c.setFont("Helvetica-Bold",12)
    c.drawString(8*mm, H-9*mm, "ALEJANDRA POMBO DESIGN STUDIO  ·  PLANNING RESTAURANTES")
    c.setFont("Helvetica",8); c.setFillColor(colors.HexColor("#C26942"))
    c.drawRightString(W-8*mm, H-9*mm, "9 septiembre 2026  ·  Actualizado reunión equipo")
    c.setFillColor(NARANJA); c.rect(0, 0, W, 4*mm, fill=1, stroke=0)
    c.setFillColor(BLANCO); c.setFont("Helvetica",5.5)
    c.drawString(8*mm, 1.5*mm, "Planning interno · No distribuir")
    c.drawRightString(W-8*mm, 1.5*mm, "APDS · RESTAURANTES · 09/09/2026")
    c.restoreState()

DEPT_REST = colors.HexColor("#8B3A00")
r0r,r1r = make_headers(DEPT_REST)
data_r = [r0r, r1r]

data_r.append(fase_sep("REMATES / ENTREGA"))
data_r += [
    prow("252","FOX + LA DESPENSA","Sofía/Naiara",
         ws("REMATES","FIN OBRA"),
         "Sep'26","SEGUIMIENTO","Remates hasta semana que viene. La Despensa stand-by."),
]

data_r.append(fase_sep("OBRA EN EJECUCIÓN"))
data_r += [
    # Cobue: apertura 21 ene → pedidos deben estar ahora (retroplanning 3 meses)
    prow("272","COBUE","Sofía/Naiara",
         ws("PEDIDOS","PEDIDOS","PEDIDOS","PEDIDOS","OBRA","OBRA","OBRA","OBRA","OBRA","OBRA","OBRA"),
         "21 ene","ATENCIÓN ALTA","Licitando. Apertura 21 ene. ⚠ PEDIDOS ya. Proyecto terminado. Ideas terraza enviadas."),
    # Mallorca: quieren terminar dic → retroplanning: pedidos oct/nov
    prow("257","MALLORCA SEVILLA","Sofía/Naiara",
         ws("OBRA","OBRA","OBRA","OBRA","PEDIDOS","PEDIDOS","PEDIDOS","OBRA","OBRA","OBRA","OBRA"),
         "Dic'26","ATENCIÓN ALTA","Demolición ejecutada. Quieren terminar diciembre."),
    # Puerto Rico: apertura mar → pedidos ene/feb → producción oct
    prow("222","PUERTO RICO","Sofía",
         ws("","VISITA","OBRA","OBRA","OBRA","OBRA","OBRA","OBRA","OBRA","OBRA","OBRA"),
         "Mar'27","ATENCIÓN ALTA","Visita+mediciones sem 19 sep. Cerrar carpintero → producir oct. Abrir marzo.",alert=True),
]

data_r.append(fase_sep("PROYECTO EJECUCIÓN"))
data_r += [
    prow("217","PASEO LAGOS 132","Sofía/Naiara",
         ws("PROY E","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E"),
         "May'27","SEGUIMIENTO","Calendario entregas renders — reunión semanal."),

    prow("276","RUBAIYAT SÃO PAULO","Naiara",
         ws("ANT.PROY","ANT.PROY","ANT.PROY","REVISIÓN","VIAJE"),
         "Feb'27","ATENCIÓN ALTA","Preparar anteproyecto. Revisión ~22 sep. Viaje 29 sep (2 noches). Obra enero."),
]

data_r.append(fase_sep("REUNIÓN / SEGUIMIENTO"))
data_r += [
    prow("243","RUBAIYAT MADRID","Naiara",
         ws("REUNIÓN"),
         "Sep'26","SEGUIMIENTO","Reunión jue 11 sep. Quieren retomar terraza."),
]

data_r.append(fase_sep("PENDIENTE DE CLIENTE / LICENCIA"))
data_r += [
    prow("172","HIPÓDROMO","Sofía/Naiara",ws(),"Pdte","SEGUIMIENTO","Sin noticias. Pendiente hablar con María PM."),
    prow("","CONCURSO DISCESUR","Sin asignar",
         ws("","","","ENTREGA","ENTREGA"),
         "Oct'26","ATENCIÓN ALTA","Diseñar creatividad en azulejo para exposición. Deadline finales octubre."),
]

data_r.append(latentes_sep())
data_r += [
    prow("","SANTANDER REST","Admón.",ws(),"—","PARADO","Gestión interna cobro."),
    prow("270","JOANN DOMINICANA","Sofía",ws(),"—","PARADO","Pendiente entrar."),
    prow("","SOPHIE","Sofía",ws(),"—","PARADO","Pendiente aceptación."),
]

gen_pdf(data_r, "/home/claude/planning_rest_9sep.pdf", DEPT_REST)

# ══════════════════════════════════════════════════════════════════════════════
# HOTELES — 7 sep 2026
# ══════════════════════════════════════════════════════════════════════════════
def hfn_hot(c,d):
    c.saveState()
    c.setFillColor(colors.HexColor("#1A3A5C"))
    c.rect(0, H-14*mm, W, 14*mm, fill=1, stroke=0)
    c.setFillColor(BLANCO); c.setFont("Helvetica-Bold",12)
    c.drawString(8*mm, H-9*mm, "ALEJANDRA POMBO DESIGN STUDIO  ·  PLANNING HOTELES")
    c.setFont("Helvetica",8); c.setFillColor(colors.HexColor("#C26942"))
    c.drawRightString(W-8*mm, H-9*mm, "9 septiembre 2026  ·  Actualizado reunión equipo")
    c.setFillColor(NARANJA); c.rect(0, 0, W, 4*mm, fill=1, stroke=0)
    c.setFillColor(BLANCO); c.setFont("Helvetica",5.5)
    c.drawString(8*mm, 1.5*mm, "Planning interno · No distribuir")
    c.drawRightString(W-8*mm, 1.5*mm, "APDS · HOTELES · 09/09/2026")
    c.restoreState()

DEPT_HOT = colors.HexColor("#1A3A5C")
r0h,r1h = make_headers(DEPT_HOT)
data_h = [r0h, r1h]

data_h.append(fase_sep("ENTREGA / CIERRE"))
data_h += [
    prow("229","VÍA 66","Jesús",
         ws("ENTREGA","PROY E","PROY E","PROY E"),
         "Ene'27","ATENCIÓN ALTA","Entrega esta semana (incompleta). ⚠ Muebles adaptación por habitación. ZZCC fase 2 enero.",alert=True),
    prow("259","CASA CORREOS","Jesús",
         ws("PROY E","PROY E","PROY E","PROY E","PROY E","PROY E","FIN OBRA"),
         "3 nov'26","ATENCIÓN ALTA","Entrega final pdte. PE deadline 3 nov. Patrimonio primero (2-3 sem). Pdte visado COAM.",alert=True),
]

data_h.append(fase_sep("MONTAJE / OBRA"))
data_h += [
    # One Shot: montaje 21 sep proveedor, fin oct → Ale ppios oct
    prow("185","ONE SHOT BILBAO","Marta",
         ws("PROY E","MONTAJE","MONTAJE","MONTAJE","ALEJANDRA"),
         "Oct'26","ATENCIÓN ALTA","Montaje proveedor 21 sep. Fin octubre. ⚠ Ale debería ir ppios octubre.",alert=True),
]

data_h.append(fase_sep("PROYECTO EJECUCIÓN"))
data_h += [
    prow("274","PSN PORTAL","Jesús",
         ws("PROY E","ENTREGA","OBRA","OBRA","OBRA","OBRA","OBRA","OBRA"),
         "Nov'26","ATENCIÓN ALTA","Cliente pendiente de ver proyecto. Entrega sep. Valoración Raúl fin sep. Obra 1 nov."),
    # Casa Almagro: anteproyecto urgente → obra nov/dic
    prow("","CASA ALMAGRO","Jesús/Marta",
         ws("ANT.PROY","ANT.PROY","ANT.PROY","ANT.PROY","OBRA","OBRA","OBRA","OBRA","OBRA","OBRA","OBRA"),
         "Feb'27","ATENCIÓN ALTA","⚠ ANT.PROY cuanto antes. Ver si vamos bien con ideas cliente. Obra nov/dic. 200k€.",alert=True),
    # Roca Maya: presentación 23 sep, FIN OBRA Sem Santa
    prow("249","ROCA MAYA","Marta/Jesús",
         ws("PROY E","PROY E","REUNIÓN","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E"),
         "Sem Santa","SEGUIMIENTO","Presentación hab. piloto 23 sep (Marta+Jesús viajan). FIN OBRA Sem Santa."),
    prow("250","RESTAURANTE HOTEL GAVÀ","Marta",
         ws("PROY E","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E","PROY E"),
         "Feb'28","SEGUIMIENTO","Restaurante hotel Barcelona. PEID F&B en curso. Constructora EC2: 15 dic. Entrega 28 feb 2028."),
]

data_h.append(fase_sep("SUPERVISIÓN / SEGUIMIENTO PUNTUAL"))
data_h += [
    prow("235","AYALA OFICINAS","Ale/Jesús",ws(),"Dic'26","ESTABLE","Seguimiento obra. Presu deco entregado. Montaje diciembre."),
    prow("260","GONZALO CÓRDOBA","Jesús",ws(),"Continuo","ESTABLE","Consultas puntuales."),
    prow("246","KANDA SÁNCHEZ PACHECO","Jesús/Marta",ws(),"—","ESTABLE","Sin noticias."),
    prow("245","KANDA CATALINA SUÁREZ","Jesús/Marta",ws(),"—","ESTABLE","Sin noticias."),
]

data_h.append(fase_sep("PENDIENTE DE CLIENTE / REACTIVANDO"))
data_h += [
    prow("212","HOTEL SEVILLA","Marta",
         ws("","REUNIÓN"),
         "2027","SEGUIMIENTO","Se reactiva. Martes 15 sep viene cliente principal. Marcar reunión para planificar."),
    prow("","BLESS","—",
         ws("PEDIDOS"),
         "—","SEGUIMIENTO","Poner en marcha unos sofás. Encargo puntual."),
    prow("253","HOTEL GIJÓN","Marta/Jesús",ws(),"—","SEGUIMIENTO","Arquitectos revisando. Habrá problemas arquitectura — pendiente planos."),
    prow("109","VINCCI VALENCIA","Marta/Jesús",ws(),"Jul'27","SEGUIMIENTO","Piloto enero 2027. Montaje final julio 2027."),
]

data_h.append(latentes_sep())
data_h += [
    prow("","PANTANO RURAL","—",ws(),"—","PARADO","—"),
    prow("06","4 MASOS","—",ws(),"—","PARADO","—"),
]

gen_pdf(data_h, "/home/claude/planning_hot_9sep.pdf", DEPT_HOT)
