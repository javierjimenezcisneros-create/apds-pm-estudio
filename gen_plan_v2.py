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

# ══════════════════════════════════════════════════════════════════════════════
# LECTOR DE EXCEL — reemplaza los datos hardcodeados
# ══════════════════════════════════════════════════════════════════════════════
import urllib.request, openpyxl, io, sys, os
from datetime import date

REPO  = "javierjimenezcisneros-create/apds-pm-estudio"
EXCEL = "PM_ESTUDIO_MASTER_COMPLETO.xlsx"

def download_excel():
    """Descarga el Excel de GitHub."""
    url = f"https://raw.githubusercontent.com/{REPO}/main/{EXCEL}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = r.read()
        print(f"✅ Excel descargado ({len(data)//1024}KB)")
        return openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    except Exception as e:
        # Fallback: buscar archivo local
        if os.path.exists(EXCEL):
            print(f"⚠ Sin internet — usando {EXCEL} local")
            return openpyxl.load_workbook(EXCEL, data_only=True)
        print(f"❌ No se puede cargar el Excel: {e}")
        sys.exit(1)

def excel_to_data(ws, dept_color, fname):
    """
    Convierte una hoja de planning del Excel en la lista data[] para gen_pdf().
    Estructura de la hoja:
      Fila 1: cabecera dept
      Fila 2: cabecera meses
      Fila 3: Nº | PROYECTO | EQUIPO | NOTAS | FIN EST | RIESGO | sem1 | sem2 ...
      Fila 4+: datos
    """
    rows = list(ws.iter_rows(values_only=True))

    # ── Detectar fila cabecera y semanas ─────────────────────────────────────
    header_idx = None
    week_cols  = {}   # col_index(0-based) → week_label

    for i, row in enumerate(rows):
        if len(row) > 1 and str(row[1] or '').strip() == 'PROYECTO':
            header_idx = i
            for j in range(6, len(row)):
                v = row[j]
                if v and isinstance(v, str) and any(c.isdigit() for c in str(v)):
                    week_cols[j] = str(v).strip()
            break

    if header_idx is None:
        print(f"   ⚠ No se encontró cabecera en {ws.title}")
        return None

    # ── Mapear etiquetas de semana del Excel a índices de WEEKS ──────────────
    week_label_to_idx = {sem: i for i,(mes,sem) in enumerate(WEEKS)}

    # ── Actualizar WEEKS desde el Excel si son distintas ─────────────────────
    # (Tomamos las semanas reales del Excel para que PDF y Excel estén sincronizados)
    excel_week_labels = [v for _,v in sorted(week_cols.items())]

    # ── Construir data[] ──────────────────────────────────────────────────────
    r0, r1 = make_headers(dept_color)
    data = [r0, r1]
    
    last_sep = None

    for row in rows[header_idx + 1:]:
        if not row: continue

        col0 = str(row[0] or '').strip()  # Nº
        col1 = str(row[1] or '').strip()  # PROYECTO / separador
        col2 = str(row[2] or '').strip()  # EQUIPO
        col3 = str(row[3] or '').strip()  # NOTAS
        col4 = str(row[4] or '').strip()  # FIN EST
        col5 = str(row[5] or '').strip()  # RIESGO

        if not col1 and not col0: continue

        # ── Separador de fase ─────────────────────────────────────────────────
        if col2 and col2.isupper() and not col0 and not col5:
            data.append(fase_sep(col2.strip()))
            last_sep = col2
            continue

        # ── Fila de vacaciones ────────────────────────────────────────────────
        if '🏖' in col1 or 'VACACIONES' in col1.upper():
            vac_data = {}
            for j, wlabel in week_cols.items():
                if j < len(row) and row[j]:
                    idx = week_label_to_idx.get(wlabel, -1)
                    if idx >= 0:
                        vac_data[idx] = str(row[j]).strip()
            # Añadir fila vac inline
            vr = [p("🏖",7,True,BLANCO,TA_CENTER), p(""),
                  p("VACACIONES",6.5,True,BLANCO), p("")]
            for i,(mes,sem) in enumerate(WEEKS):
                txt = vac_data.get(i,'')
                vr.append(p(txt, 7, False, BLANCO, TA_CENTER))
            vr += [p(""), p(""), p("")]
            data.append(vr)
            continue

        # ── Separador latentes ────────────────────────────────────────────────
        if 'LATENTE' in col2.upper() or 'PAUSADO' in col2.upper():
            data.append(latentes_sep())
            continue

        # ── Fila de proyecto ──────────────────────────────────────────────────
        if not col1 or len(col1) < 2: continue

        # Construir semanas[]
        semanas_list = [''] * N
        for j, wlabel in week_cols.items():
            if j < len(row) and row[j]:
                v = str(row[j]).strip()
                if v not in ('None', '', '—'):
                    idx = week_label_to_idx.get(wlabel, -1)
                    if 0 <= idx < N:
                        semanas_list[idx] = v

        alert = '⚠' in col3 or col5 in ('ATENCIÓN MÁXIMA',)

        data.append(prow(
            num     = col0,
            nombre  = col1,
            equipo  = col2,
            semanas = semanas_list,
            fin_est = col4,
            riesgo  = col5 if col5 else 'SEGUIMIENTO',
            nota    = col3,
            alert   = alert,
        ))

    return data

# ══════════════════════════════════════════════════════════════════════════════
# MAIN — descargar Excel y generar los 3 PDFs
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    today  = date.today()
    suffix = today.strftime('%d%b').lower()   # p.ej. "09sep"

    print(f"\n🗓  {today.strftime('%d de %B de %Y')}")
    wb = download_excel()

    DEPT_VIV  = GRANATE
    DEPT_REST = colors.HexColor("#8B3A00")
    DEPT_HOT  = colors.HexColor("#1A3A5C")

    sheets = [
        ('VIVIENDA',      DEPT_VIV,  f"/home/claude/planning_viv_{suffix}.pdf"),
        ('RESTAURANTES',  DEPT_REST, f"/home/claude/planning_rest_{suffix}.pdf"),
        ('HOTELES',       DEPT_HOT,  f"/home/claude/planning_hot_{suffix}.pdf"),
    ]

    for sheet_name, dept_color, fname in sheets:
        if sheet_name not in wb.sheetnames:
            print(f"⚠ Hoja {sheet_name} no encontrada en el Excel")
            continue
        ws = wb[sheet_name]
        data = excel_to_data(ws, dept_color, fname)
        if data and len(data) > 2:
            gen_pdf(data, fname, dept_color)
        else:
            print(f"⚠ Sin datos en {sheet_name}")

    print("\n✅ Plannings generados desde Excel")
