"""
generate_app.py — APDS PM Estudio
Lee PM_ESTUDIO_MASTER_COMPLETO.xlsx y genera docs/index.html
inyectando MASTER_DATA, GLOBAL_DATA, PLANNING_DATA y META como JS.

Fuentes:
  - Hoja "MASTER GLOBAL"  → MASTER_DATA + GLOBAL_DATA
  - Hoja "PLANNING"        → PLANNING_DATA

No depende de gen_plan_v2.py. No hardcodea números de columna.
"""

import json
import re
import unicodedata
from datetime import datetime, date
from pathlib import Path

import openpyxl

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
EXCEL_PATH = Path("PM_ESTUDIO_MASTER_COMPLETO.xlsx")
TEMPLATE_HEAD = Path("head.html")
TEMPLATE_APP  = Path("app.js")
OUTPUT_PATH   = Path("docs/index.html")

# Nombres de hojas — se buscan por coincidencia parcial (case-insensitive)
# para tolerar variaciones menores como "PLANNING POMBO" vs "PLANNING"
SHEET_MASTER_KEY   = "MASTER GLOBAL"
SHEET_PLANNING_KEY = "PLANNING"

# Columnas esperadas en MASTER GLOBAL (cabeceras, case-insensitive strip)
COL_MASTER = {
    "proyecto":      "PROYECTO",
    "dpto":          "DPTO",
    "equipo":        "EQUIPO",
    "estado":        "ESTADO",
    "proximo_hito":  "PRÓXIMO HITO",
    "fecha_hito":    "FECHA PRÓXIMO HITO",
    "bloqueador":    "BLOQUEADOR",
    "constructora":  "CONSTRUCTORA",
    "fase":          "FASE",
    "atencion":      "ATENCIÓN",
    "fin_obra":      "FIN OBRA PREVISTO",
    "montaje":       "MONTAJE PREVISTO",
    "fin_oficial":   "FINALIZACIÓN OFICIAL",
    "obs":           "OBSERVACIONES",
}

# Valores válidos de ATENCIÓN (normalizados)
ATENCION_VALIDOS = {"ATENCIÓN MÁXIMA", "ATENCIÓN ALTA", "SEGUIMIENTO", "ESTABLE"}

# Columnas fijas del Planning (cabeceras que NO son semanas)
PLANNING_FIXED_COLS = {"DPTO", "PROYECTO", "RESPONSABLE", "FASE", "PRÓXIMO HITO", "CONTROL"}

# Filas de sección en Planning (empiezan con ▸)
SECCION_PREFIX = "▸"


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def slugify(texto: str) -> str:
    """Convierte texto a slug ASCII: minúsculas, sin tildes, espacios→_ ."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.lower().strip()
    texto = re.sub(r"[^a-z0-9\s]", "", texto)
    texto = re.sub(r"\s+", "_", texto)
    return texto


def make_id(nombre: str, dpto: str) -> str:
    """Genera un id estable: slug(nombre)__slug(dpto)."""
    sufijos = {"vivienda": "viv", "restaurantes": "rest", "hoteles": "hot"}
    dpto_norm = slugify(dpto)
    sufijo = sufijos.get(dpto_norm, dpto_norm[:3] if dpto_norm else "")
    return f"{slugify(nombre)}__{sufijo}"


def normalizar_dpto(raw: str) -> str:
    """Normaliza el departamento a 'vivienda' | 'restaurantes' | 'hoteles'."""
    if not raw:
        return raw
    r = raw.strip().upper()
    if r in ("VIV", "VIVIENDA"):
        return "vivienda"
    if r in ("REST", "RESTAURANTES", "RESTAURANTE"):
        return "restaurantes"
    if r in ("HOT", "HOTELES", "HOTEL"):
        return "hoteles"
    return raw.strip().lower()


def parse_equipo(raw: str) -> list:
    """
    Convierte 'RESPONSABLE / COLABORADORA' → ['responsable', 'colaboradora'].
    Admite también '+' como separador adicional.
    """
    if not raw:
        return []
    # Separadores: / o +
    partes = re.split(r"[/+]", str(raw))
    return [p.strip() for p in partes if p.strip()]


def parse_fecha(valor) -> str | None:
    """Convierte fecha de Excel a string ISO 'YYYY-MM-DD' o None."""
    if valor is None:
        return None
    if isinstance(valor, (datetime, date)):
        return valor.strftime("%Y-%m-%d") if isinstance(valor, datetime) else valor.isoformat()
    s = str(valor).strip()
    if not s or s == "—" or s == "-":
        return None
    # Intenta parsear formatos comunes: DD/MM/YYYY, D/M/YY, etc.
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return s  # devuelve el string original si no puede parsear


def val(cell) -> str | None:
    """Valor de celda como string limpio, o None si vacía."""
    if cell is None:
        return None
    v = cell.value if hasattr(cell, "value") else cell
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def week_label(fecha_lunes) -> str | None:
    """
    Convierte una fecha de lunes (date/datetime o string 'D MMM') a 'WNN/YYYY'.
    Ejemplos: date(2026,10,5) → 'W41/2026'
              '5 OCT' → usa el año actual implícito del contexto
    """
    if fecha_lunes is None:
        return None

    if isinstance(fecha_lunes, (datetime, date)):
        d = fecha_lunes if isinstance(fecha_lunes, date) else fecha_lunes.date()
        iso = d.isocalendar()
        return f"W{iso[1]:02d}/{iso[0]}"

    # String tipo '5 OCT', '28 SEP', '12 OCT', etc.
    s = str(fecha_lunes).strip()
    meses = {
        "ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
        "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12
    }
    m = re.match(r"(\d{1,2})\s+([A-ZÁÉÍÓÚ]{3})", s.upper())
    if m:
        dia = int(m.group(1))
        mes = meses.get(m.group(2))
        if mes:
            # Año: usar el año actual; si el mes es menor que el mes actual
            # y la diferencia es grande, asumir año siguiente
            hoy = date.today()
            anyo = hoy.year
            if mes < hoy.month - 3:
                anyo += 1
            try:
                d = date(anyo, mes, dia)
                iso = d.isocalendar()
                return f"W{iso[1]:02d}/{iso[0]}"
            except ValueError:
                pass
    return None


# ---------------------------------------------------------------------------
# Lector de MASTER GLOBAL
# ---------------------------------------------------------------------------

def leer_master(ws) -> tuple[list, list]:
    """
    Lee la hoja MASTER GLOBAL.
    Retorna (master_data, global_data).
    Identifica columnas por cabecera, no por índice fijo.
    """
    # --- Encontrar fila de cabeceras ---
    header_row = None
    col_map = {}  # clave_interna → índice de columna (0-based)

    for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
        if row is None:
            continue
        # Busca la fila que contenga "PROYECTO"
        row_str = [str(c).strip().upper() if c else "" for c in row]
        if "PROYECTO" in row_str:
            header_row = row_idx
            # Construye mapa cabecera→índice
            cabeceras_esperadas = {v.upper(): k for k, v in COL_MASTER.items()}
            for ci, celda in enumerate(row_str):
                if celda in cabeceras_esperadas:
                    col_map[cabeceras_esperadas[celda]] = ci
            break

    if header_row is None:
        raise ValueError(f"No se encontró la fila de cabeceras en la hoja '{SHEET_MASTER}'")

    master_data = []
    global_data = []

    for row in ws.iter_rows(min_row=header_row + 2, values_only=True):
        # Celda de proyecto
        nombre = None
        if "proyecto" in col_map:
            nombre = row[col_map["proyecto"]] if col_map["proyecto"] < len(row) else None
            nombre = str(nombre).strip() if nombre else None

        if not nombre or nombre.upper() in ("PROYECTO", "NAN", "NONE", ""):
            continue
        # Ignora filas de sección o separadores visuales
        if nombre.startswith(SECCION_PREFIX) or nombre.startswith("▶") or nombre.startswith("—"):
            continue

        def get(key):
            idx = col_map.get(key)
            if idx is None or idx >= len(row):
                return None
            return row[idx]

        dpto_raw = val(get("dpto")) or ""
        dpto = normalizar_dpto(dpto_raw)
        proyecto_id = make_id(nombre, dpto)

        equipo_raw = val(get("equipo")) or ""
        equipo = parse_equipo(equipo_raw)

        atencion_raw = val(get("atencion")) or ""
        atencion = atencion_raw.strip().upper()
        if atencion not in ATENCION_VALIDOS:
            atencion = None  # no almacenamos valores inválidos

        # --- MASTER_DATA ---
        master_entry = {
            "id":          proyecto_id,
            "nombre":      nombre,
            "dpto":        dpto,
            "equipo":      equipo,
            "estado":      val(get("estado")),
            "fase":        val(get("fase")),
            "constructora": val(get("constructora")),
            "fin_obra":    parse_fecha(get("fin_obra")),
            "montaje":     val(get("montaje")),   # string original ('05/10 – 16/10')
            "fin_oficial": parse_fecha(get("fin_oficial")),
            "obs":         val(get("obs")),
            "ficha_url":   None,
        }
        master_data.append(master_entry)

        # --- GLOBAL_DATA ---
        global_entry = {
            "id":           proyecto_id,
            "atencion":     atencion,
            "proximo_hito": val(get("proximo_hito")),
            "fecha_hito":   parse_fecha(get("fecha_hito")),
            "bloqueador":   val(get("bloqueador")),
            "diagnostico":  None,  # reservado para lógica futura
        }
        global_data.append(global_entry)

    return master_data, global_data


# ---------------------------------------------------------------------------
# Lector de PLANNING
# ---------------------------------------------------------------------------

def leer_planning(ws) -> dict:
    """
    Lee la hoja PLANNING unificada.
    Identifica columnas por cabecera dinámica.
    Retorna PLANNING_DATA.
    """
    # El Planning tiene esta estructura de filas:
    #   fila 1: título del documento
    #   fila 2: agrupación de meses (SEP, OCT, NOV...)
    #   fila 3: fechas de lunes (28 SEP, 5 OCT, 12 OCT...)  ← cabeceras de semana
    #   fila 4: cabeceras de columnas (DPTO, PROYECTO, RESPONSABLE, FASE, PRÓXIMO HITO, ..., CONTROL)
    #   fila 5+: datos (filas de sección ignoradas, filas de proyecto procesadas)

    all_rows = list(ws.iter_rows(values_only=True))

    if len(all_rows) < 4:
        raise ValueError(f"La hoja '{SHEET_PLANNING}' no tiene suficientes filas")

    # --- Identificar fila de cabeceras de columna ---
    header_row_idx = None
    col_header_map = {}  # nombre_cabecera → índice columna

    for ri, row in enumerate(all_rows):
        row_str = [str(c).strip().upper() if c else "" for c in row]
        if "PROYECTO" in row_str and "DPTO" in row_str:
            header_row_idx = ri
            for ci, c in enumerate(row_str):
                if c:
                    col_header_map[c] = ci
            break

    if header_row_idx is None:
        raise ValueError(f"No se encontró la fila de cabeceras en la hoja '{SHEET_PLANNING}'")

    # --- Identificar fila de fechas de semana (fila inmediatamente anterior a cabeceras) ---
    fecha_row_idx = header_row_idx - 1
    fecha_row = all_rows[fecha_row_idx] if fecha_row_idx >= 0 else []

    # --- Determinar índices de columnas fijas ---
    idx_dpto       = col_header_map.get("DPTO")
    idx_proyecto   = col_header_map.get("PROYECTO")
    # CONTROL puede no existir o estar al final
    idx_control    = col_header_map.get("CONTROL")

    # --- Identificar columnas de semana ---
    # Son las columnas entre PRÓXIMO HITO y CONTROL (o fin de fila)
    # La identificación se hace por la fila de fechas: toda celda con una fecha válida
    # en esa fila y que esté después de PRÓXIMO HITO es una columna de semana.
    idx_hito = col_header_map.get("PRÓXIMO HITO") or col_header_map.get("PROXIMO HITO", 4)
    idx_fin  = idx_control if idx_control is not None else len(fecha_row)

    semana_cols = []  # lista de (col_idx, week_label)
    todas_semanas = []

    for ci in range(idx_hito + 1, idx_fin):
        if ci >= len(fecha_row):
            break
        celda_fecha = fecha_row[ci]
        if celda_fecha is None:
            continue
        wl = week_label(celda_fecha)
        if wl:
            semana_cols.append((ci, wl))
            if wl not in todas_semanas:
                todas_semanas.append(wl)

    # --- Leer filas de proyectos ---
    proyectos = []
    seccion_actual = None

    for row in all_rows[header_row_idx + 1:]:
        if row is None:
            continue

        # --- Detectar fila de sección (el ▸ puede aparecer en cualquier columna) ---
        es_seccion = False
        for ci_check in range(min(3, len(row))):  # revisar las primeras 3 columnas
            v_check = row[ci_check]
            if v_check and (SECCION_PREFIX in str(v_check) or "▶" in str(v_check)):
                seccion_actual = str(v_check).lstrip("▸▶ ").strip()
                es_seccion = True
                break
        if es_seccion:
            continue

        # Valor del campo PROYECTO
        nombre_raw = row[idx_proyecto] if idx_proyecto is not None and idx_proyecto < len(row) else None
        nombre = str(nombre_raw).strip() if nombre_raw else None

        if not nombre or nombre.lower() in ("nan", "none", ""):
            continue

        # Ignorar la fila de cabeceras si aparece repetida
        if nombre.upper() == "PROYECTO":
            continue

        # Obtener departamento
        dpto_raw = row[idx_dpto] if idx_dpto is not None and idx_dpto < len(row) else None
        dpto_raw = str(dpto_raw).strip() if dpto_raw else ""
        dpto = normalizar_dpto(dpto_raw)

        # Generar id consistente con MASTER_DATA
        proyecto_id = make_id(nombre, dpto)

        # Construir timeline: solo semanas con actividad
        timeline = []
        for ci, wl in semana_cols:
            if ci >= len(row):
                continue
            celda = row[ci]
            texto = str(celda).strip() if celda else ""
            if not texto or texto.lower() in ("nan", "none", ""):
                continue
            # Una actividad por celda (el Excel actual no tiene múltiples por celda)
            timeline.append({
                "semana": wl,
                "actividades": [
                    {"texto": texto, "nivel": "principal"}
                ]
            })

        proyectos.append({
            "id":       proyecto_id,
            "dpto":     dpto,
            "grupo":    seccion_actual,
            "timeline": timeline,
        })

    # --- Construir lista de montajes desde timeline ---
    # Un montaje es cualquier semana con actividad "MONTAJE", "PREENTREGA" o "ENTREGA"
    TIPOS_MONTAJE = {"MONTAJE", "PREENTREGA", "ENTREGA"}
    montajes = []
    for p in proyectos:
        semanas_montaje = [
            e["semana"]
            for e in p["timeline"]
            if any(a["texto"].upper() in TIPOS_MONTAJE for a in e["actividades"])
        ]
        if semanas_montaje:
            # Buscar el tipo de la última actividad relevante
            ultimo_tipo = None
            for e in reversed(p["timeline"]):
                for a in e["actividades"]:
                    if a["texto"].upper() in TIPOS_MONTAJE:
                        ultimo_tipo = a["texto"].upper()
                        break
                if ultimo_tipo:
                    break
            montajes.append({
                "id":           p["id"],
                "nombre":       None,  # se cruza con MASTER_DATA en la APP
                "semanas":      semanas_montaje,
                "tipo":         ultimo_tipo or "MONTAJE",
            })

    return {
        "semanas":   todas_semanas,
        "proyectos": proyectos,
        "montajes":  montajes,
    }


# ---------------------------------------------------------------------------
# Generador principal
# ---------------------------------------------------------------------------

def iso_week_hoy() -> str:
    hoy = date.today()
    iso = hoy.isocalendar()
    return f"W{iso[1]:02d}/{iso[0]}"


def generar_html(master_data, global_data, planning_data) -> str:
    """Carga head.html + app.js e inyecta el bloque DATA."""

    head = TEMPLATE_HEAD.read_text(encoding="utf-8") if TEMPLATE_HEAD.exists() else ""
    app  = TEMPLATE_APP.read_text(encoding="utf-8")  if TEMPLATE_APP.exists()  else ""

    meta = {
        "updated":    datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "hoy_semana": iso_week_hoy(),
        "perfiles":   ["javi", "alejandra"],
    }

    data_block = (
        "<script>\n"
        f"const META          = {json.dumps(meta,          ensure_ascii=False, indent=2)};\n"
        f"const MASTER_DATA   = {json.dumps(master_data,   ensure_ascii=False, indent=2)};\n"
        f"const GLOBAL_DATA   = {json.dumps(global_data,   ensure_ascii=False, indent=2)};\n"
        f"const PLANNING_DATA = {json.dumps(planning_data, ensure_ascii=False, indent=2)};\n"
        "</script>"
    )

    # Construye el HTML final
    html = f"""<!DOCTYPE html>
<html lang="es">
{head}
<body>
{data_block}
<script>
{app}
</script>
</body>
</html>"""

    return html


def encontrar_hoja(wb, keyword: str):
    """
    Busca una hoja cuyo nombre contenga 'keyword' (case-insensitive).
    Preferencia: coincidencia exacta > coincidencia parcial.
    Lanza ValueError si no encuentra ninguna.
    """
    keyword_up = keyword.upper()
    # 1. Coincidencia exacta
    for nombre in wb.sheetnames:
        if nombre.upper() == keyword_up:
            return wb[nombre], nombre
    # 2. Coincidencia parcial
    for nombre in wb.sheetnames:
        if keyword_up in nombre.upper():
            return wb[nombre], nombre
    raise ValueError(
        f"No se encuentra hoja con '{keyword}'. "
        f"Hojas disponibles: {wb.sheetnames}"
    )


def main():
    print(f"[generate_app] Leyendo {EXCEL_PATH}...")

    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"No se encuentra el Excel: {EXCEL_PATH}")

    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)

    ws_master, nombre_master = encontrar_hoja(wb, SHEET_MASTER_KEY)
    ws_planning, nombre_planning = encontrar_hoja(wb, SHEET_PLANNING_KEY)

    print(f"[generate_app] Procesando '{nombre_master}'...")
    master_data, global_data = leer_master(ws_master)
    print(f"  → {len(master_data)} proyectos en MASTER_DATA")

    print(f"[generate_app] Procesando '{nombre_planning}'...")
    planning_data = leer_planning(ws_planning)
    print(f"  → {len(planning_data['proyectos'])} proyectos en PLANNING_DATA")
    print(f"  → {len(planning_data['semanas'])} semanas: {planning_data['semanas'][0]} … {planning_data['semanas'][-1]}")

    print(f"[generate_app] Generando {OUTPUT_PATH}...")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    html = generar_html(master_data, global_data, planning_data)
    OUTPUT_PATH.write_text(html, encoding="utf-8")

    print(f"[generate_app] ✓ Generado {OUTPUT_PATH} ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
