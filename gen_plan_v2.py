from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import datetime

PAGE = landscape(A3)
W = float(PAGE[0])
H = float(PAGE[1])
MARGIN = 6*mm

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
    "PROY B":    colors.HexColor("#BDD7EE"),
    "PROY E":    colors.HexColor("#70B0D8"),
    "PROY DECO": colors.HexColor("#C9B8E8"),
    "ANT.PROY":  colors.HexColor("#D4C4F0"),
    "OBRA":      colors.HexColor("#F5C07A"),
    "FIN OBRA":  colors.HexColor("#2E7D32"),
    "PEDIDOS":   colors.HexColor("#FFE384"),
    "MONTAJE":   colors.HexColor("#E87878"),
    "REUNIÓN":   colors.HexColor("#A8D8A8"),
    "VISITA":    colors.HexColor("#A8D8A8"),
    "ENTREGA":   colors.HexColor("#5FAD5F"),
    "APERTURA":  colors.HexColor("#5FAD5F"),
    "CIERRE":    colors.HexColor("#A8D8A8"),
    "ALEJANDRA": colors.HexColor("#8B2252"),
    "RENDERS":   colors.HexColor("#C8C8C8"),
    "RENDERS":   colors.HexColor("#C8C8C8"),
    "REMATES":   colors.HexColor("#F5C07A"),
    "VIAJE":     colors.HexColor("#8B2252"),
    "REVISIÓN":  colors.HexColor("#BDD7EE"),
    "PLANOS":    colors.HexColor("#BDD7EE"),
    "DEMOL.":    colors.HexColor("#F5C07A"),
    "PDTE LIC":  colors.HexColor("#D0CEC8"),
    "PENDIENTE": colors.HexColor("#EBEBEB"),
    "FUERA":     colors.HexColor("#888888"),
    "⚠":        colors.HexColor("#FF4040"),
    "LA DESP.":  colors.HexColor("#E87878"),
}
TXT = {
    "ENTREGA": BLANCO, "APERTURA": BLANCO, "ALEJANDRA": BLANCO,
    "FUERA": BLANCO, "⚠": BLANCO, "PROY E": BLANCO, "VIAJE": BLANCO,
    "FIN OBRA": BLANCO,
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
    ("AGO","25 AGO","HOY"),
    ("SEP","1 SEP",""),("SEP","8 SEP",""),("SEP","15 SEP",""),("SEP","22 SEP",""),("SEP","29 SEP",""),
    ("OCT","6 OCT",""),("OCT","13 OCT",""),("OCT","20 OCT",""),("OCT","27 OCT",""),
    ("NOV","3 NOV",""),
]
N = len(WEEKS)  # 11

USABLE = W - 2*MARGIN
COL_C  = 9*mm
COL_P  = 40*mm
COL_R  = 20*mm
COL_FE = 16*mm
COL_RI = 18*mm
COL_NO = 38*mm   # notas
FIXED  = COL_C+COL_P+COL_R+COL_FE+COL_RI
COL_W  = (USABLE-FIXED)/N

COLS = [COL_C,COL_P,COL_R]+[COL_W]*N+[COL_FE,COL_RI] + [COL_W]*N + [COL_NO, COL_FE, COL_RI]

def make_header_rows():
    # Fila meses
    r1 = ["","",""]
    prev_mes = None
    for mes, sem, _ in WEEKS:
        if mes != prev_mes:
            r1.append(p(mes, 7, True, BLANCO, TA_CENTER))
            prev_mes = mes
        else:
            r1.append("")
    r1 += ["", ""]

    # Fila semanas
    r2 = [p("Nº",7,True,BLANCO,TA_CENTER), p("PROYECTO", 6.5, True, BLANCO, TA_CENTER),
          p("RESP.", 6.5, True, BLANCO, TA_CENTER)]
    for mes, sem, _ in WEEKS:
        is_now = sem == "25 AGO"
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

def prow(nombre, equipo, semanas, fin_est="", riesgo="", nota="", codigo="", fase="", negrita_nombre=False, alert=False):
    """
    semanas: list of N strings (or empty), matching WEEKS order
    """
    row = [
        p(codigo, 6, False, GRIS_L, TA_CENTER),
        p(nombre, 7.5, True, colors.HexColor("#C0392B") if alert else GRANATE),
        p(equipo, 6.5, color=GRIS),
    ]
    for i, (mes, sem, _) in enumerate(WEEKS):
        txt = semanas[i] if i < len(semanas) else ""
        if not txt and fase:
            txt = fase
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

def vac_row(por_semana):
    row = [p("🏖",7,True,BLANCO,TA_CENTER), p("VACACIONES",6.5,True,BLANCO), p("",6)]
    for i,(mes,sem,_) in enumerate(WEEKS):
        txt = por_semana[i] if i<len(por_semana) else ""
        row.append(p(txt,7,False,BLANCO,TA_CENTER))
    row += [p(""),p(""),p("")]
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
    col = 3
    prev_mes = None
    start = 3
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
        for ci in range(3, 3+N):
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
    canvas.drawRightString(W-8*mm, H-9*mm, f"27 agosto 2026  ·  Actualizado reunión equipo")
    canvas.setFillColor(GRANATE); canvas.rect(0,0,W,6*mm,fill=1,stroke=0)
    canvas.setFillColor(BLANCO); canvas.setFont("Helvetica",6)
    canvas.drawString(8*mm,2*mm,"Planning interno · No distribuir")
    canvas.drawRightString(W-8*mm,2*mm,f"APDS · {dept} · 27/08/2026")
    canvas.restoreState()

def gen(dept, activos, latentes, notas, vac, col_dept, fname, supervision=None):
    def hfn(c,d): header_fn(c,d,dept,col_dept)
    doc = SimpleDocTemplate(fname, pagesize=PAGE,
        leftMargin=MARGIN, rightMargin=MARGIN, topMargin=16*mm, bottomMargin=8*mm)
    r1,r2 = make_header_rows()
    data = [r1, r2]
    for pr in activos: data.append(pr)
    if supervision:
        data.append(sep_row("SUPERVISIÓN / SEGUIMIENTO PUNTUAL"))
        for pr in supervision: data.append(pr)
    data.append(vac_row(vac))
    if latentes:
        data.append(sep_row("LATENTES / PAUSADOS"))
        for pr in latentes: data.append(pr)
    if notas:
        data.append(sep_row("NOTAS"))
        for nota in notas:
            data.append([p(""), p(nota,5.5,False,GRIS_L)] + [""]*(N+3))
    _n = len(data)
    _rh = [8*mm,10*mm]+[8*mm]*(_n-2)
    t = Table(data, colWidths=COLS, rowHeights=_rh, repeatRows=2)
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
# ══════════════════════════════════════════════════════════════════════════════# ─── DATOS 27 AGO 2026 ────────────────────────────────────────────────────────
# idx: 0=25AGO  1=1SEP  2=8SEP  3=15SEP  4=22SEP  5=29SEP
#      6=6OCT   7=13OCT 8=20OCT 9=27OCT  10=3NOV

ROJO_H = colors.HexColor("#8B3A00")
AZUL_H = colors.HexColor("#1A3A5C")

# ══════════════════════════════════════════════════════════════════════════════
# RESTAURANTES — actualizado 27 ago 2026
# ══════════════════════════════════════════════════════════════════════════════
rest_activos = [
    prow("FOX + LA DESPENSA","Sofía/Naiara",
         ws(s0="REMATES",s1="REMATES",s2="REMATES",s3="APERTURA"),
         "23 sep","SEGUIMIENTO",fase="REMATES",
         nota="Amboage pendiente antes del 17 sep. Apertura oficial 23 sep.",codigo="252"),
    prow("PUERTO RICO","Sofía",
         ws(s7="VISITA"),
         "Mar/Abr'27","ATENCIÓN ALTA",fase="PROY E",
         nota="Decidir carpintero (Amboage descartado). Mediciones 2ª sem oct. Fab nov-ene. Instalación feb.",codigo="222"),
    prow("RUBAIYAT MADRID","Naiara",
         ws(s0="PROY DECO",s1="PROY DECO",s2="ENTREGA"),
         "Sep'26","SEGUIMIENTO",fase="PROY DECO",
         nota="Cerrando deco terraza. Pendiente: cortina, mueble, ampliación. Terminar semana sep.",codigo="243"),
    prow("RUBAIYAT SÃO PAULO","Naiara",
         ws(s4="REVISIÓN",s5="VIAJE"),
         "2027","ATENCIÓN ALTA",fase="ANT.PROY",
         nota="Preparar anteproyecto. Revisión ~22 sep. Viaje 29 sep (2 noches). Obra enero por fases.",codigo="276"),
    prow("BERNABÉU","Naiara",
         ws(s0="REMATES",s1="CIERRE"),
         "Sep'26","SEGUIMIENTO",fase="REMATES",
         nota="Terminado. Pendiente: cierre números, 1 mesa+perchas. Mesas estropeadas: decisión cliente.",codigo="203"),
    prow("MALLORCA SEVILLA","Sofía/Naiara",
         ws(s0="REUNIÓN"),
         "2027","ATENCIÓN ALTA",fase="OBRA",
         nota="Licencia concedida. Demolición ejecutada. Reunión sem que viene. A construir.",codigo="257"),
    prow("HIPÓDROMO","Sofía/Naiara",
         ws(),
         "Pdte","SEGUIMIENTO",fase="PDTE LIC",
         nota="Sin noticias. Pendiente hablar con María PM.",codigo="172"),
    prow("VIV JOANN (Anteproy.)","Sofía",
         ws(),
         "2027","SEGUIMIENTO",fase="PROY B",
         nota="Arrancando PB hoy. Planning enviado. Obra desde 2027.",codigo="270"),
    prow("COBUE","Sofía/Naiara",
         ws(s0="PROY E",s1="ENTREGA"),
         "21 ene","ATENCIÓN ALTA",fase="OBRA",
         nota="Entrega valoración+renders sem que viene. Licitando. Apertura 21 enero.",codigo="272"),
    prow("PASEO LAGOS 132","Sofía/Naiara",
         ws(),
         "May'27","SEGUIMIENTO",fase="PROY E",
         nota="Pendiente cerrar: acabados, techos, carpintería, iluminación, domótica.",codigo="217"),
    prow("CARBON","Sofía",
         ws(s0="REMATES",s1="REMATES"),
         "Sep'26","SEGUIMIENTO",
         nota="Proyecto antiguo. Remate aislamiento acústico pendiente de ejecutar."),
    prow("CLÍNICA LONGEVIDAD","—",
         ws(),"—","SEGUIMIENTO",nota="Sin novedades."),
]
rest_latentes = [
    prow("SANTANDER REST","Admón.",ws(),"—","PARADO",nota="Gestión interna cobro."),
    prow("JOANN DOMINICANA","Sofía",ws(),"—","PARADO",nota="Pendiente entrar.",codigo="270"),
    prow("SOPHIE","Sofía",ws(),"—","PARADO",nota="Pendiente aceptación."),
]
rest_vac  = [""]*11
rest_notas = ["🏖 Sofía: disponible · Naiara: disponible"]

gen("RESTAURANTES", rest_activos, rest_latentes, rest_notas,
    rest_vac, ROJO_H, "/home/claude/planning_rest_27ago.pdf")

# ══════════════════════════════════════════════════════════════════════════════
# VIVIENDA — actualizado 27 ago 2026
# ══════════════════════════════════════════════════════════════════════════════
viv_activos = [
    prow("PEDRAZA","Olatz/Paula",
         ws(s0="REMATES",s1="REUNIÓN"),
         "Sep'26","SEGUIMIENTO",fase="REMATES",
         nota="Reunión lun 1 sep con clientes+constructora. Lista repasos. 2ª fase caballerías pdte.",codigo="224"),
    prow("ZAHARA","Paula",
         ws(s0="REMATES",s1="REMATES"),
         "Sep'26","SEGUIMIENTO",fase="REMATES",
         nota="Pedidos hechos. Dormitorio de abajo pendiente (post-verano). Ale con listas deco.",codigo=""),
    prow("VALENCIA","Sara/Andrea",
         ws(s0="ENTREGA",s2="REMATES"),
         "29 ago","ATENCIÓN ALTA",
         nota="⚠ ENTREGA viernes 29. Mob. exterior mediados sep. Problemas obra asumidos.",codigo="241",alert=True),
    prow("ALCALÁ 58","Alicia/Javi",
         ws(s0="OBRA",s1="FIN OBRA"),
         "Sep'26","ATENCIÓN ALTA",fase="OBRA",
         nota="⚠ Va retrasado. Comunicar nueva fecha al cliente. Reunión constructora esta sem.",codigo="223"),
    prow("LA FLORIDA","Paula",
         ws(s1="PROY DECO",s4="MONTAJE",s5="MONTAJE"),
         "Sep'26","ATENCIÓN ALTA",fase="OBRA",
         nota="Deco organizada 2ª sem sep. Paula: visitar obra para confirmar. Montaje última sem sep.",codigo="264"),
    prow("LA RINCONADA","Cristina/Nela",
         ws(s9="FIN OBRA",s10="ENTREGA"),
         "Nov'26","ATENCIÓN ALTA",fase="OBRA",
         nota="⚠ Presu deco sin enviar — Ale revisar URGENTE. Solo mesa/sillas/sofá en fabric. Nela visita. FIN OBRA fin oct (pdte aceptación cliente).",codigo="254"),
    prow("VIUDA DE ALDAMA 3","Nela/Andrea",
         ws(s1="REUNIÓN"),
         "Nov'26","ATENCIÓN ALTA",fase="PROY E",
         nota="Reunión jue 3 sep (Natalia+Raúl+Ale+Nela). Presupuestos obra+deco pendientes actualizar.",codigo="271"),
    prow("VIUDA DE ALDAMA 2","Sin asignar",
         ws(),"2027","SEGUIMIENTO",
         nota="Nuevo proyecto. Organizar con cliente en septiembre.",codigo="273"),
    prow("SANTANDER VIV","Sara",
         ws(s3="VISITA",s4="PROY DECO"),
         "Dic'26","ATENCIÓN ALTA",fase="PROY E",
         nota="Visita obra sem 14 sep. Reuniones deco sem 21 sep. Montaje diciembre.",codigo="216"),
    prow("IBIZA","Sara",
         ws(s2="OBRA",s3="OBRA",s4="OBRA"),
         "Dic'26","SEGUIMIENTO",fase="PDTE LIC",
         nota="Obra parada municipio hasta sep. Pagos pendientes clientes. Montaje diciembre.",codigo="242"),
    prow("HERMOSILLA","Nela/Olatz",
         ws(),"Mar'27","SEGUIMIENTO",fase="PENDIENTE",
         nota="Cliente de vuelta. Olatz contactar al volver. Sin info constructora.",codigo="258"),
    prow("MONTESQUINZA","Sara",
         ws(),
         "Mar'27","ATENCIÓN ALTA",fase="OBRA",
         nota="⚠ Notificación licencia/DR recibida — revisar. Obra avanzando. Revisar presupuesto.",codigo="268"),
    prow("GAMAL STO. DOMINGO","Sofía/Olatz",
         ws(s0="REMATES"),"—","SEGUIMIENTO",
         nota="Montaje realizado. Confirmar si hay remates o se cierra.",codigo="231"),
    prow("CAMINO SUR 70","Cristina/Nela",
         ws(s0="MONTAJE",s1="VISITA",s2="REMATES"),
         "Sep'26","ATENCIÓN ALTA",
         nota="⚠ Visita clientes LUN 1 SEP — Olatz presente. Fallos Contraluz iluminación. Remates papel.",codigo="267",alert=True),
    prow("CAMINO SUR 35","Nela",
         ws(),"2027","SEGUIMIENTO",fase="RENDERS",
         nota="Pancho con correcciones renders (6 fases totales). Sin deco todavía.",codigo="211"),
    prow("TORRE VALENCIA","Paula",
         ws(s1="REUNIÓN"),"2027","SEGUIMIENTO",fase="PROY E",
         nota="Replanteo iluminación realizado. Cliente sin decisiones domótica. Paula visita próxima sem.",codigo="239"),
    prow("PASEO LAGOS 105","Sara/Andrea",
         ws(s3="REUNIÓN"),"2027","SEGUIMIENTO",fase="PROY B",
         nota="Reunión 15 sep: render + cerrar presentación. Obra retrasa a ppios 2027 (humedades).",codigo="255"),
    prow("VALCARCE","Paula",
         ws(s0="REMATES",s1="REMATES"),"—","SEGUIMIENTO",
         nota="Remates papel (David da largas). Remates Raúl: cliente espere 2 semanas.",codigo=""),
    prow("PESQUERA","Paula",
         ws(s0="PEDIDOS"),"Dic'26","SEGUIMIENTO",fase="OBRA",
         nota="Deco en oficina pendiente enviar. Cocina definida. Constructora en marcha. Cliente: navidades.",codigo="265"),
    prow("PASEO LAGOS 121","Olatz",
         ws(s1="REUNIÓN"),"Feb'27","ATENCIÓN ALTA",fase="PROY DECO",
         nota="⚠ Reunión 2 sep. Presentación Nela pendiente revisión Ale — URGENTE.",codigo="275"),
    prow("VIV PALOMA RD","Olatz/Andrea",
         ws(s1="REUNIÓN"),"Jul'27","SEGUIMIENTO",fase="PROY DECO",
         nota="Reunión agosto con Ale. Siguiente reunión septiembre.",codigo="232"),
    prow("TEPEYAC","Paula",
         ws(),"2027","SEGUIMIENTO",fase="PENDIENTE",
         nota="Parado. Reunión pendiente Raúl+Paula+cliente para presupuesto obra.",codigo="262"),
    prow("ABUBILLA","Paula",
         ws(s2="REMATES"),"Sep'26","SEGUIMIENTO",
         nota="Remates sofá y cortinas. Semana del 7 sep.",codigo=""),
]
viv_latentes = [
    prow("ANA HONTANAR","Paula",ws(),"—","PARADO",nota="Después de verano.",codigo="225"),
    prow("JAIME PESQUERA","Paula",ws(),"—","PARADO",nota="Después de verano.",codigo="265"),
    prow("HABITACIÓN ABI","Andrea",ws(),"—","PARADO",nota="Pdte feedback presupuesto."),
    prow("ANTIC COLONIAL","—",ws(),"—","PARADO"),
    prow("MONTALBÁN","Olatz",ws(),"—","PARADO"),
]
viv_vac  = [""]*11
viv_notas = [
    "⚠ URGENTE: VALENCIA entrega vie 29 · CAMINO SUR 70 visita lun 1 sep Olatz · RINCONADA presu deco Ale · LAGOS 121 presentación Ale · MONTESQUINZA revisar notificación DR",
]
gen("VIVIENDA", viv_activos, viv_latentes, viv_notas,
    viv_vac, GRANATE, "/home/claude/planning_viv_27ago.pdf")

# ══════════════════════════════════════════════════════════════════════════════
# HOTELES — actualizado 27 ago 2026
# ══════════════════════════════════════════════════════════════════════════════
hot_activos = [
    prow("DON RAMÓN","Marta",
         ws(s1="MONTAJE",s2="REMATES"),"1 sep","ATENCIÓN ALTA",
         nota="Montaje 1 sep. Marta y Ale viajan. Revisión remates en montaje.",codigo="70"),
    prow("ONE SHOT BILBAO","Marta",
         ws(s7="MONTAJE",s8="MONTAJE"),"Oct'26","ATENCIÓN ALTA",fase="PROY E",
         nota="⚠ Cliente+MO cambiaron elementos unilateralmente — hablar con MO. Fin oct. Visita 1-2 días.",codigo="185",alert=True),
    prow("ROCA MAYA","Marta/Jesús",
         ws(),"Sem Santa","SEGUIMIENTO",fase="PROY E",
         nota="Muestras y proveedores OK. Detalles listos sep para fabricar. Entrega Sem Santa: hab→ZC→azotea.",codigo="249"),
    prow("HOTEL ÚNICO BCN","Marta",
         ws(s0="PROY E",s1="PROY E"),"Sep'26","SEGUIMIENTO",fase="PROY E",
         nota="Fichas técnicas más definidas. Auna propuesto proveedor. Entregar todo sep y licitar.",codigo="250"),
    prow("VÍA 66","Jesús",
         ws(s0="PROY E",s1="ENTREGA",s2="PROY E",s3="PROY E"),"Ene'27","ATENCIÓN ALTA",fase="PROY E",
         nota="⚠ Entrega 4 sep (2ª+3ª plantas). MO con retrasos. ZC fase 2 enero.",codigo="229",alert=True),
    prow("PSN PORTAL","Jesús",
         ws(s0="PROY E",s1="PROY E",s2="PROY E",s3="ENTREGA"),"Nov'26","ATENCIÓN ALTA",fase="PROY E",
         nota="Pdte revisión Ale. Entrega sep. Valoración Raúl fin sep. Obra 1 nov.",codigo="274"),
    prow("CASA ALMAGRO","Jesús/Marta",
         ws(s0="PROY E",s1="PROY E",s2="PROY E",s3="PROY E",s4="PROY E",s6="OBRA",s7="OBRA",s8="OBRA",s9="OBRA"),
         "Feb'27","ATENCIÓN ALTA",fase="PROY E",
         nota="Kickoff realizado. Restaurante en hotel Madrid. Obra mediados nov/ppios dic. ~2 meses. Presu obra 200k€.",codigo=""),
    prow("HOTEL SEVILLA","Marta",
         ws(),"—","SEGUIMIENTO",
         nota="Proyecto actualizado. Ampliación no aceptada. Obra casi parada. Cliente busca mob. por libre.",codigo="212"),
    prow("HOTEL GIJÓN","Marta/Jesús",
         ws(),"—","SEGUIMIENTO",
         nota="Problemas instalaciones condicionan techos. Pendiente últimos planos.",codigo="253"),
    prow("VINCCI VALENCIA","Marta/Jesús",
         ws(),"Jul'27","SEGUIMIENTO",
         nota="Piloto enero 2027. Montaje final julio/agosto 2027.",codigo="109"),
    prow("MARTÍNEZ CAMPOS","Jesús",ws(),"—","SEGUIMIENTO",nota="Sin noticias.",codigo="269"),
    prow("CASA KORREOS","Jesús",ws(),"—","SEGUIMIENTO",nota="Sin noticias.",codigo="259"),
]
hot_supervision = [
    prow("GONZALO CÓRDOBA","Jesús",ws(),"Continuo","ESTABLE",nota="Sin noticias.",codigo="260"),
    prow("AYALA OFICINAS","Ale/Jesús",
         ws(s0="PROY DECO"),"Dic'26","ESTABLE",
         nota="Presupuesto deco entregado esta semana. Montaje diciembre.",codigo="235"),
    prow("KANDA SÁNCHEZ PACHECO","Jesús/Marta",ws(),"—","ESTABLE",nota="Sin noticias.",codigo="246"),
    prow("KANDA CATALINA SUÁREZ","Jesús/Marta",ws(),"—","ESTABLE",nota="Sin noticias.",codigo="245"),
]
hot_latentes = [
    prow("PANTANO RURAL","—",ws(),"—","PARADO",codigo=""),
    prow("4 MASOS","—",ws(),"—","PARADO",codigo="06"),
    prow("BLESS","—",ws(),"—","PARADO"),
]
hot_vac  = [""]*11
hot_notas = ["⚠ URGENTE: DON RAMÓN montaje 1 sep (Marta+Ale) · VÍA 66 entrega 4 sep · ONE SHOT BILBAO hablar con MO esta semana"]

gen("HOTELES", hot_activos, hot_latentes, hot_notas,
    hot_vac, AZUL_H, "/home/claude/planning_hot_27ago.pdf",
    supervision=hot_supervision)
