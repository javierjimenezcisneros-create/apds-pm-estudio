from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import datetime

PAGE = landscape(A4)
W = float(PAGE[0])
H = float(PAGE[1])
MARGIN = 7*mm

# ── Paleta APDS ──────────────────────────────────────────────────────────────
GRANATE  = colors.HexColor("#5C1831")
NARANJA  = colors.HexColor("#DB7733")
PAPER    = colors.HexColor("#F4F1EC")
BLANCO   = colors.white
GRIS     = colors.HexColor("#4A4A4A")
GRIS_L   = colors.HexColor("#9C9088")
GRIS_H   = colors.HexColor("#E8E4E0")  # header alt

# ── Colores de actividad ──────────────────────────────────────────────────────
ACT = {
    "PROY B":    colors.HexColor("#BDD7EE"),  # azul claro
    "PROY E":    colors.HexColor("#70B0D8"),  # azul medio
    "PROY DECO": colors.HexColor("#C9B8E8"),  # lila
    "OBRA":      colors.HexColor("#F5C07A"),  # naranja
    "PEDIDOS":   colors.HexColor("#FFE384"),  # amarillo
    "MONTAJE":   colors.HexColor("#E87878"),  # rojo
    "REUNIÓN":   colors.HexColor("#A8D8A8"),  # verde claro
    "ENTREGA":   colors.HexColor("#5FAD5F"),  # verde oscuro
    "ALEJANDRA": colors.HexColor("#8B2252"),  # granate oscuro
    "RENDERS":   colors.HexColor("#C8C8C8"),  # gris
    "⚠":        colors.HexColor("#FF4040"),  # rojo alerta
    "FUERA":     colors.HexColor("#888888"),  # gris oscuro
    "REMATES":   colors.HexColor("#F5C07A"),  # naranja claro
    "VISITA":    colors.HexColor("#A8D8A8"),
    "MUEST.":    colors.HexColor("#FFE384"),
    "ANT.PROY":  colors.HexColor("#C9B8E8"),
    "VIAJE":     colors.HexColor("#8B2252"),
    "RCL":       colors.HexColor("#A8D8A8"),
    "LA DESP.":  colors.HexColor("#E87878"),
    "PLANOS":    colors.HexColor("#BDD7EE"),
    "DEMOL.":    colors.HexColor("#F5C07A"),
    "FIN OBRA":  colors.HexColor("#5FAD5F"),
    "RENDER":    colors.HexColor("#C8C8C8"),
}
TXT = {
    "ENTREGA": BLANCO, "ALEJANDRA": BLANCO, "FUERA": BLANCO,
    "⚠": BLANCO, "PROY E": BLANCO, "VIAJE": BLANCO,
}

def act_color(txt):
    if not txt: return None
    for k in ACT:
        if k in str(txt).upper():
            return ACT[k]
    return None

def act_txt_color(txt):
    if not txt: return GRIS
    for k in TXT:
        if k in str(txt).upper():
            return TXT[k]
    return GRIS

def p(text, size=7, bold=False, color=GRIS, align=TA_LEFT, italic=False):
    if text is None: text = ""
    fn = "Helvetica-Bold" if bold else ("Helvetica-Oblique" if italic else "Helvetica")
    return Paragraph(str(text), ParagraphStyle('_', fontName=fn, fontSize=size,
        textColor=color, leading=size*1.35, alignment=align, wordWrap='LTR'))

# ── Semanas ───────────────────────────────────────────────────────────────────
# Hoy: jue 30 jul 2026 — incluimos semana actual y las 11 siguientes
WEEKS = [
    ("JUL","27 JUL",""),
    ("AGO","3 AGO",""),("AGO","10 AGO",""),("AGO","17 AGO",""),("AGO","24 AGO",""),
    ("SEP","1 SEP",""),("SEP","8 SEP",""),("SEP","15 SEP",""),("SEP","22 SEP",""),("SEP","29 SEP",""),
    ("OCT","6 OCT",""),
]
N = len(WEEKS)  # 11

USABLE = W - 2*MARGIN
COL_P  = 34*mm   # proyecto
COL_R  = 20*mm   # responsable
COL_FE = 11*mm   # fin estimado
COL_RI = 16*mm   # riesgo
COL_NO = 38*mm   # notas
FIXED  = COL_P + COL_R + COL_FE + COL_RI + COL_NO
COL_W  = (USABLE - FIXED) / N

COLS = [COL_P, COL_R] + [COL_W]*N + [COL_NO, COL_FE, COL_RI]

def make_header_rows():
    # Fila meses
    r1 = ["", ""]
    prev_mes = None
    for mes, sem, _ in WEEKS:
        if mes != prev_mes:
            r1.append(p(mes, 7, True, BLANCO, TA_CENTER))
            prev_mes = mes
        else:
            r1.append("")
    r1 += ["", ""]

    # Fila semanas
    r2 = [p("PROYECTO", 6.5, True, BLANCO, TA_CENTER),
          p("RESP.", 6.5, True, BLANCO, TA_CENTER)]
    for mes, sem, _ in WEEKS:
        is_now = sem == "27 JUL"
        r2.append(p(sem, 5.5, is_now, NARANJA if is_now else BLANCO, TA_CENTER))
    r2 += [p("NOTAS / ESTADO ACTUAL", 6, True, BLANCO, TA_LEFT),
           p("FIN EST.", 6, True, BLANCO, TA_CENTER),
           p("RIESGO", 6, True, BLANCO, TA_CENTER)]
    return r1, r2

def leyenda_row():
    items = [("PROY B","Proyecto básico"),("PROY E","Proyecto ejec."),
             ("PROY DECO","Proy.deco"),("OBRA","Obra"),("PEDIDOS","Pedidos"),
             ("MONTAJE","Montaje"),("REUNIÓN","Reunión"),("ENTREGA","Entrega"),
             ("ALEJANDRA","Ale presente"),("RENDERS","Renders"),("⚠","Alerta"),("FUERA","Fuera")]
    parts = []
    for code, label in items:
        bg = ACT.get(code, PAPER)
        tc_ = TXT.get(code, GRIS)
        parts.append(p(f" {code} ", 5, color=tc_))
    # Build as simple text row
    row = [p("LEYENDA:", 5.5, True, GRIS_L)] + [""] + [p("PROY B=azul claro · PROY E=azul · PROY DECO=lila · OBRA=naranja · PEDIDOS=amarillo · MONTAJE=rojo · REUNIÓN=verde · ENTREGA=verde osc. · ALEJANDRA=granate · ⚠=alerta · FUERA=gris", 5.5, False, GRIS_L)] + [""]*(N-1) + ["",""]
    return row

def prow(nombre, equipo, semanas, fin_est="", riesgo="", nota="", negrita_nombre=False, alert=False):
    """
    semanas: list of N strings (or empty), matching WEEKS order
    """
    row = [
        p(nombre, 7.5, True, colors.HexColor("#C0392B") if alert else GRANATE),
        p(equipo, 6.5, color=GRIS),
    ]
    for i, (mes, sem, _) in enumerate(WEEKS):
        txt = semanas[i] if i < len(semanas) else ""
        bg = act_color(txt)
        tc_ = act_txt_color(txt) if txt else GRIS
        row.append(p(txt or "", 5.5, False, tc_, TA_CENTER))
    row.append(p(nota, 6, False, GRIS, TA_LEFT))
    row.append(p(fin_est, 6, False, GRIS, TA_CENTER))
    # Riesgo color
    rcol = {"ATENCIÓN MÁXIMA": colors.HexColor("#C0392B"),
            "ATENCIÓN ALTA": colors.HexColor("#E07030"),
            "SEGUIMIENTO": colors.HexColor("#1A5C1A"),
            "ESTABLE": colors.HexColor("#1A5C1A"),
            "PARADO": GRIS_L}.get(riesgo, GRIS)
    row.append(p(riesgo, 5, True, rcol, TA_CENTER))
    return row

def sep_row(label):
    return [p(f"  {label}", 6.5, True, GRIS_L)] + [""]*(N+4)

def vac_row(semanas):
    row = [p("🏖 VACACIONES", 6.5, True, BLANCO, TA_CENTER), p("", 6)]
    for i,(mes,sem,_) in enumerate(WEEKS):
        txt = semanas[i] if i < len(semanas) else ""
        row.append(p(txt, 5, False, BLANCO, TA_CENTER))
    row += [p(""), p("")]
    return row

def build_table_style(data):
    ts = TableStyle([
        ('FONTNAME',(0,0),(-1,-1),'Helvetica'),
        ('FONTSIZE',(0,0),(-1,-1),7),
        ('BACKGROUND',(0,0),(-1,0),GRANATE),
        ('BACKGROUND',(0,1),(-1,1),colors.HexColor("#7A2844")),
        ('TEXTCOLOR',(0,0),(-1,1),BLANCO),
        ('ROWBACKGROUNDS',(0,2),(-1,-1),[BLANCO,PAPER]),
        ('GRID',(0,0),(-1,-1),0.15,colors.HexColor("#D0C8C0")),
        ('LINEABOVE',(0,2),(-1,2),0.5,GRANATE),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),2),
        ('BOTTOMPADDING',(0,0),(-1,-1),2),
        ('LEFTPADDING',(0,0),(-1,-1),2),
        ('RIGHTPADDING',(0,0),(-1,-1),2),
    ])
    # Highlight semana actual (27 JUL = col index 2)
    HOY_COL = 2
    ts.add('BACKGROUND',(HOY_COL,0),(HOY_COL,-1),colors.HexColor("#FFF3E8"))
    ts.add('LINEAFTER',(HOY_COL,0),(HOY_COL,-1),0.8,NARANJA)
    ts.add('LINEBEFORE',(HOY_COL,0),(HOY_COL,-1),0.8,NARANJA)

    # Merge month headers (row 0)
    col = 2
    prev_mes = None
    start = 2
    for i,(mes,sem,_) in enumerate(WEEKS):
        if mes != prev_mes:
            if prev_mes is not None:
                ts.add('SPAN',(start,0),(col-1,0))
            start = col
            prev_mes = mes
        col += 1
    ts.add('SPAN',(start,0),(col-1,0))

    # Color cells by activity
    for ri, row in enumerate(data):
        if ri < 2: continue
        for ci in range(2, 2+N):
            cell_val = row[ci]
            if hasattr(cell_val,'text'):
                txt = cell_val.text
            elif isinstance(cell_val, str):
                txt = cell_val
            else:
                txt = ""
            bg = act_color(txt)
            if bg:
                ts.add('BACKGROUND',(ci,ri),(ci,ri),bg)

    # Sep rows
    for ri, row in enumerate(data):
        if not row: continue
        first = row[0]
        txt = first.text if hasattr(first,'text') else str(first)
        if 'LATENTE' in txt or 'VACACIONES' in txt or 'NOTAS' in txt or 'LEYENDA' in txt:
            bg = colors.HexColor("#3A3A3A") if 'VAC' in txt else GRIS_H
            if 'VAC' in txt:
                ts.add('BACKGROUND',(0,ri),(-1,ri),colors.HexColor("#2C2C2C"))
            elif '\U0001f3d6' in txt or 'VACACIONES' in txt:
                ts.add('BACKGROUND',(0,ri),(-1,ri),colors.HexColor('#2C4A2C'))
            elif 'LATENTE' in txt:
                ts.add('BACKGROUND',(0,ri),(-1,ri),colors.HexColor("#EDE8E0"))
                ts.add('LINEABOVE',(0,ri),(-1,ri),0.8,GRANATE)
            else:
                ts.add('BACKGROUND',(0,ri),(-1,ri),GRIS_H)
    return ts

def header_fn(canvas, doc, dept, col_dept):
    canvas.saveState()
    canvas.setFillColor(col_dept)
    canvas.rect(0, H-15*mm, float(W), 15*mm, fill=1, stroke=0)
    canvas.setFillColor(BLANCO); canvas.setFont("Helvetica-Bold",11)
    canvas.drawString(8*mm, H-9*mm, f"ALEJANDRA POMBO DESIGN STUDIO  ·  PLANNING {dept.upper()}")
    canvas.setFont("Helvetica",8)
    canvas.drawRightString(W-8*mm, H-9*mm, f"30 julio 2026  ·  Actualizado reunión equipo")
    canvas.setFillColor(GRANATE); canvas.rect(0,0,W,6*mm,fill=1,stroke=0)
    canvas.setFillColor(BLANCO); canvas.setFont("Helvetica",6)
    canvas.drawString(8*mm,2*mm,"Planning interno · No distribuir")
    canvas.drawRightString(W-8*mm,2*mm,f"APDS · {dept} · 30/07/2026")
    canvas.restoreState()

def gen(dept, activos, latentes, notas, vac, col_dept, fname):
    def hfn(c,d): header_fn(c,d,dept,col_dept)
    doc = SimpleDocTemplate(fname, pagesize=PAGE,
        leftMargin=MARGIN, rightMargin=MARGIN, topMargin=17*mm, bottomMargin=8*mm)
    r1,r2 = make_header_rows()
    data = [r1, r2]
    for pr in activos: data.append(pr)
    data.append(vac_row(vac))
    data.append(sep_row("LATENTES / PAUSADOS"))
    if latentes:
        for pr in latentes: data.append(pr)
    if notas:
        data.append(sep_row("NOTAS Y ALERTAS"))
        for nota in notas:
            row = [p(nota, 5.5, False, GRIS_L)] + [""]*(N+3)
            data.append(row)
    t = Table(data, colWidths=COLS, repeatRows=2)
    t.setStyle(build_table_style(data))
    doc.build([t], onFirstPage=hfn, onLaterPages=hfn)
    print(f"✅ {fname}")

# ─── SEMANAS helper: list de N strings ───────────────────────────────────────
def ws(s0=None,s1=None,s2=None,s3=None,s4=None,s5=None,s6=None,s7=None,s8=None,s9=None,s10=None):
    return [s0 or "",s1 or "",s2 or "",s3 or "",s4 or "",
            s5 or "",s6 or "",s7 or "",s8 or "",s9 or "",s10 or ""]
# idx:       0=27JUL  1=3AGO  2=10AGO  3=17AGO  4=24AGO  5=1SEP  6=8SEP  7=15SEP  8=22SEP  9=29SEP  10=6OCT

# ══════════════════════════════════════════════════════════════════════════════
# RESTAURANTES
# ══════════════════════════════════════════════════════════════════════════════
ROJO_H = colors.HexColor("#8B3A00")

rest_activos = [
    prow("FOX + LA DESPENSA","Sofía/Naiara",
         ws("FIN CARP.","REMATES","LA DESP.","LA DESP."),
         "Jul 2026","SEGUIMIENTO", nota="Carpintero termina esta sem. La Despensa (PB) se reactiva. Ejecutar ago."),
    prow("PUERTO RICO","Sofía",
         ws("MUEST.","OBRA","OBRA","OBRA","OBRA","OBRA"),
         "Ene 2027","ATENCIÓN ALTA", nota="Esta sem: muestras + cambios. Obra en marcha. Dos valoraciones carpintero."),
    prow("RUBAIYAT MADRID","Naiara",
         ws("REUNIÓN","PEDIDOS"),
         "Jul 2026","SEGUIMIENTO", nota="Hoy: reunión iluminación + pedidos. Estimar fechas cierre."),
    prow("BERNABÉU","Naiara",
         ws("PEDIDOS","⚠","MONTAJE"),
         "Ago 2026","ATENCIÓN ALTA", nota="Todo pedido. Estores esta sem. Montaje sem 10 ago confirmado.",alert=True),
    prow("MALLORCA SEVILLA","Sofía/Naiara",
         ws("","","","","","PROY E"),
         "2027","SEGUIMIENTO", nota="Sin novedades."),
    prow("HIPÓDROMO","Sofía/Naiara",
         ws("","","","","","","","","PROY DECO"),
         "2027","SEGUIMIENTO", nota="Sin licencia ni licitación. Hablar con PM para pausar presión."),
    prow("VIV JOANN (Anteproyecto)","Sofía",
         ws("REUNIÓN","FUERA","FUERA","FUERA"),
         "2027","SEGUIMIENTO", nota="Reunión jue 31: renders dormitorios. Anteproyecto (obra desde 2027)."),
    prow("COBUE","Sofía/Naiara",
         ws("REUNIÓN","FUERA","FUERA","","","OBRA","OBRA"),
         "Ene 2027","ATENCIÓN ALTA", nota="Reunión mar 28. PB listo. Ale por videollamada. Listado cambios cliente."),
    prow("RUBAIYAT SÃO PAULO","Naiara",
         ws("","","","","","ANT.PROY","VIAJE"),
         "Ene 2027","ATENCIÓN ALTA", nota="Anteproyecto 1ª sem sep. Viaje São Paulo 2ª sem sep."),
    prow("CLÍNICA LONGEVIDAD","—",
         ws(),
         "—","SEGUIMIENTO", nota="Sin feedback de clientes."),
    prow("PASEO LAGOS 132 (Viv.)","Sofía/Naiara",
         ws("RENDER"),
         "May 2027","SEGUIMIENTO", nota="Render baño pendiente visto bueno cliente."),
]
rest_latentes = [
    prow("SANTANDER REST","Admón.",ws(),"—","PARADO"),
    prow("JOANN DOMINICANA","Sofía",ws(),"—","PARADO"),
    prow("SOPHIE","Sofía",ws(),"—","PARADO"),
]
rest_notas = [
    "🏖 SOFÍA: vacaciones 10-24 ago · NAIARA: disponible todo agosto.",
]

gen("RESTAURANTES", rest_activos, rest_latentes, rest_notas, ['', 'Marta·Jesús', 'Sofía·Jesús', 'Sofía·Naiara·Olatz·Jesús', 'Sofía·Olatz', 'Sara', '', '', '', '', ''], ROJO_H,
    "/home/claude/planning_rest_30jul.pdf")

# ══════════════════════════════════════════════════════════════════════════════
# VIVIENDA
# ══════════════════════════════════════════════════════════════════════════════
viv_activos = [
    prow("PEDRAZA","Olatz/Paula",
         ws("MONTAJE","REMATES","ENTREGA"),
         "Ago 2026","ATENCIÓN ALTA", nota="Montaje mañana. Oficial sem 3 ago. Objetivo: terminado el 15 (llega cliente)."),
    prow("ZAHARA","Paula",
         ws("MONTAJE","REMATES"),
         "Ago 2026","ATENCIÓN ALTA", nota="Obra termina esta sem. Montaje empezado este fin de semana."),
    prow("VALENCIA","Sara/Andrea",
         ws("⚠","","","","","","","","","",""),
         "— ⚠","ATENCIÓN MÁXIMA", nota="⚠ BLOQUEADO. Indecisiones cliente mal gestionadas. Sin nueva fecha. Conversación urgente.",alert=True),
    prow("ALCALÁ 58","Alicia/Javi",
         ws("OBRA","OBRA","OBRA","OBRA","FIN OBRA"),
         "Fin ago","SEGUIMIENTO", nota="Avance lento por carpintería. Fin ago. Pendiente cerrar fecha con cliente."),
    prow("LA FLORIDA","Paula",
         ws("OBRA","OBRA","OBRA","OBRA","MONTAJE","MONTAJE"),
         "Sep 2026","ATENCIÓN ALTA", nota="Pedidos hechos. Obra empezada. Termina mediados sep. Montaje acto seguido."),
    prow("LA RINCONADA","Cristina/Nela",
         ws("PLANOS","PEDIDOS","OBRA","OBRA","OBRA","⚠","MONTAJE"),
         "Oct 2026","ATENCIÓN ALTA", nota="Nela actualiza planos hoy. Obra en marcha. Posible retraso a ppios oct."),
    prow("VIUDA DE ALDAMA","Nela/Andrea",
         ws("PROY E","PROY E","PROY E","PROY E","","","PROY DECO"),
         "Nov 2026","ATENCIÓN ALTA", nota="Nela valora sótano con Andrea. Sin constructora. Contratación poco avanzada."),
    prow("SANTANDER VIV","Sara",
         ws("OBRA","OBRA","OBRA","OBRA","OBRA","PROY DECO"),
         "Dic 2026","ATENCIÓN ALTA", nota="Obra lenta. Pedidos obra sin cerrar (algunos los hace el estudio). Presu deco sin avanzar."),
    prow("IBIZA","Sara",
         ws("OBRA","FUERA","FUERA","FUERA","FUERA","OBRA","PROY DECO"),
         "Dic 2026","SEGUIMIENTO", nota="Parada hasta sep. Cliente esperando a Ale. Al arrancar: preparar proy deco."),
    prow("HERMOSILLA","Nela/Olatz",
         ws("","","","","","PROY DECO"),
         "Mar 2027","SEGUIMIENTO", nota="Sin feedback de cliente ni constructora."),
    prow("MONTESQUINZA","Sara",
         ws("DEMOL.","DEMOL.","DEMOL.","DEMOL.","","OBRA","OBRA"),
         "Mar 2027","SEGUIMIENTO", nota="Demolición ago. Pendiente mini proyecto terraza para vecinos."),
    prow("CAMINO SUR 70","Cristina/Nela",
         ws("OBRA"),
         "—","SEGUIMIENTO", nota="Avanzando. Sin novedades específicas."),
    prow("CAMINO SUR 35","Nela",
         ws("RENDERS","RENDERS","OBRA"),
         "2027","SEGUIMIENTO", nota="Renders en agosto. Trabajar con el equipo en ago."),
    prow("TORRE VALENCIA","Paula",
         ws("REUNIÓN","PROY E","PROY E"),
         "2027","SEGUIMIENTO", nota="Visita viernes. Actualizar decisiones: cosas del proyecto no son viables."),
    prow("VALCARCE","Paula",
         ws("REMATES"),
         "—","SEGUIMIENTO", nota="Obra terminada. Remates sin programar. Extra deco pedido. Repasar lista."),
    prow("PESQUERA","Paula",
         ws("REUNIÓN"),
         "—","SEGUIMIENTO", nota="Pedidos realizados. Reunión con Ale pendiente para ver necesidades."),
    prow("PASEO LAGOS 121","Olatz",
         ws("","","","","","PROY DECO","PROY DECO"),
         "Feb 2027","SEGUIMIENTO", nota="Cliente muy exigente. Reunión pendiente. Objetivo: obra antes navidades."),
    prow("VIV PALOMA RD","Olatz/Andrea",
         ws("","","","","","PROY DECO"),
         "Jul 2027","SEGUIMIENTO", nota="Arrancar proyecto deco sep/oct 2026."),
    prow("TEPEYAC","Paula",
         ws(),
         "2027","SEGUIMIENTO", nota="Sin reunión programada con cliente."),
]
viv_latentes = [
    prow("ANA HONTANAR","Paula",ws(),"—","PARADO"),
    prow("JAIME PESQUERA","Paula",ws(),"—","PARADO"),
    prow("HABITACIÓN ABI","Andrea",ws(),"—","PARADO"),
    prow("ANTIC COLONIAL","—",ws(),"—","PARADO"),
    prow("MONTALBÁN","Olatz",ws(),"—","PARADO"),
]
viv_notas = [
    "🏖 VACACIONES AGO: Alejandra · Javi · Andrea · Paula · Sara (3-21 ago) · Sofía (10-24 ago) · Naiara (17-21 ago) · Olatz (17-28 ago) · NELA: disponible todo agosto.",
    "⚠ SANTANDER + IBIZA: el estudio ha aceptado hacer pedidos de obra — revisar este alcance.",
]

gen("VIVIENDA", viv_activos, viv_latentes, viv_notas, ['', 'Ale·Javi·Andrea·Paula·Sara·Marta·Jesús·Cris', 'Ale·Javi·Andrea·Paula·Sara·Sofía·Jesús', 'Ale·Javi·Andrea·Paula·Sara·Sofía·Naiara·Olatz·Jesús', 'Ale·Javi·Andrea·Paula·Sara·Olatz', 'Sara', '', '', '', '', ''], GRANATE,
    "/home/claude/planning_viv_30jul.pdf")

# ══════════════════════════════════════════════════════════════════════════════
# HOTELES
# ══════════════════════════════════════════════════════════════════════════════
AZUL_H = colors.HexColor("#1A3A5C")

hot_activos = [
    prow("DON RAMÓN","Marta",
         ws("OBRA","OBRA","MONTAJE","MONTAJE","ENTREGA","ALEJANDRA"),
         "Ago 2026","ATENCIÓN ALTA", nota="Problema mueble cocinas/carpintero (no resp. estudio). Sem 24: montaje+Ale. Pendiente confirmar con Irene."),
    prow("ONE SHOT BILBAO","Marta",
         ws("FUERA","FUERA","FUERA","FUERA","FUERA","FUERA","OBRA","MONTAJE"),
         "Nov 2026","SEGUIMIENTO", nota="Montaje movido a mediados nov. Solo gestión dudas proveedor."),
    prow("ROCA MAYA","Marta/Jesús",
         ws("⚠","OBRA","OBRA","OBRA","OBRA","OBRA"),
         "Mar 2027","ATENCIÓN ALTA", nota="⚠ Sin detalle de clima. Marta prepara resumen para Jesús (actúa sem que viene sin Marta).",alert=True),
    prow("HOTEL ÚNICO BCN","Marta",
         ws("REUNIÓN","","","","","OBRA"),
         "2027","SEGUIMIENTO", nota="PM cliente con solicitudes ya documentadas. Materiales se validan en obra."),
    prow("VÍA 66","Jesús",
         ws("⚠","OBRA","OBRA","OBRA","OBRA"),
         "Mar 2027","SEGUIMIENTO", nota="⚠ Error interno: muebles necesitan adaptación por habitación. Dibujar cada uno a medida.",alert=True),
    prow("HOTEL SEVILLA","Marta",
         ws("","","","","","OBRA"),
         "2027","SEGUIMIENTO", nota="Actualizado tras visita. Honorarios ampliación presentados. Sin planning realista."),
    prow("HOTEL GIJÓN","Marta/Jesús",
         ws(),
         "—","SEGUIMIENTO", nota="Sin noticias. Instalaciones afectan a techos. Preparando licencia."),
    prow("VINCCI VALENCIA","Marta/Jesús",
         ws("","","","","","","OBRA"),
         "2027","SEGUIMIENTO", nota="Proyecto terminado. Renders propuestos sin respuesta. Obra en cimentación."),
    prow("MARTÍNEZ CAMPOS","Jesús",
         ws("FUERA","FUERA","FUERA","FUERA","FUERA","REUNIÓN"),
         "2027","SEGUIMIENTO", nota="Sin info. Reunión cuando vuelva Jesús."),
    prow("CASA KORREOS","Jesús",
         ws("FUERA","FUERA","FUERA","FUERA","FUERA","REUNIÓN"),
         "2027","SEGUIMIENTO", nota="Sin info. Reunión cuando vuelva Jesús."),
    prow("GONZALO CÓRDOBA","Jesús",
         ws(),
         "Continuo","ESTABLE", nota="Dudas resueltas. Sin contacto."),
    prow("AYALA OFICINAS","Ale/Jesús",
         ws(),
         "Continuo","ESTABLE", nota="Sin contacto."),
    prow("KANDA SÁNCHEZ PACHECO","Jesús/Marta",
         ws(),
         "—","ESTABLE", nota="Sin feedback."),
    prow("KANDA CATALINA SUÁREZ","Jesús/Marta",
         ws(),
         "—","ESTABLE", nota="Sin feedback."),
]
hot_latentes = [
    prow("PANTANO RURAL","—",ws(),"—","PARADO"),
    prow("4 MASOS","—",ws(),"—","PARADO"),
    prow("BLESS","—",ws(),"—","PARADO"),
]
hot_notas = [
    "⚠ ROCA MAYA: sin detalle de clima · Marta ha preparado resumen para Jesús · la semana que viene Jesús lo gestiona (sin Marta).",
    "⚠ VÍA 66: error interno · muebles tipo necesitan adaptación por habitación · hay que tener cada mueble dibujado a medida.",
    "📅 DON RAMÓN: problema mueble cocinas/carpintero (no responsabilidad del estudio) · pintores y escayolas sem del 17 ago · montaje mobiliario sem del 24 ago (Marta) · ALE: ir sem del 24, lo más tarde posible · pendiente confirmar con Irene.",
    "📅 ONE SHOT BILBAO: montaje movido a mediados noviembre · solo gestión de dudas de proveedor.",
    "📅 HOTEL ÚNICO BCN: PM del cliente con muchas solicitudes ya documentadas · materiales se validan en obra.",
    "📅 HOTEL SEVILLA: actualizado tras visita · honorarios de ampliación presentados · sin planning realista.",
    "📅 HOTEL GIJÓN: sin noticias · instalaciones afectan a techos · sin planning · preparando licencia.",
    "📅 VINCCI VALENCIA: proyecto terminado · renders propuestos sin respuesta · obra en cimentación.",
    "🏖 JESÚS: vacaciones hasta 13 ago · MARTA: vacaciones 3-7 ago.",
]

gen("HOTELES", hot_activos, hot_latentes, hot_notas, ['', 'Marta·Jesús', 'Sofía·Jesús', 'Olatz·Jesús', 'Olatz', 'Sara', '', '', '', '', ''], AZUL_H,
    "/home/claude/planning_hot_30jul.pdf")
