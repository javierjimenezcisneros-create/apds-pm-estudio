#!/usr/bin/env python3
"""
bizneo_sync.py — Sincronización de ausencias Bizneo → PM_ESTUDIO_MASTER_COMPLETO.xlsx
Pombo Estudio · Sistema Operativo PM · Fase 1 — Base de datos de ausencias

SEGURIDAD:
  - La URL del calendario se lee ÚNICAMENTE de la variable de entorno BIZNEO_ICAL_URL.
  - Nunca se incluye la URL en código, logs ni archivos versionados.
  - Los eventos anónimos se conservan como SIN_IDENTIFICAR sin atribución por suposición.

GARANTÍAS:
  - Fallo de descarga    → preserva datos existentes, sin cambios al Excel.
  - Fallo de parsing     → preserva datos existentes, sin cambios al Excel.
  - Evento desaparecido  → Estado = CANCELADA; el registro histórico se conserva.
  - Segunda ejecución    → no duplica (UID_ICAL como clave primaria).
  - Evento actualizado   → solo reescribe si LAST-MODIFIED es más reciente.

USO:
  BIZNEO_ICAL_URL=<url> python bizneo_sync.py
  BIZNEO_ICAL_URL=<url> BIZNEO_DRY_RUN=1 python bizneo_sync.py   # no guarda
  BIZNEO_ICAL_URL=<url> BIZNEO_LOG_LEVEL=DEBUG python bizneo_sync.py

INTEGRACIÓN FUTURA (no implementada aquí — ver bizneo_integration_notes.md):
  Paso 2: generate_app.py debe llamar a extract_ausencias() que lea esta hoja
          y cruce NOMBRE_PILA + SEMANAS_AFECTADAS con los proyectos del Gantt.
  Paso 3: gen_plan_v2.py debe leer AUSENCIAS para marcar celdas FUERA (#888888)
          en las semanas donde el responsable esté ausente.
  Paso 4: GitHub Actions ejecuta este script ANTES de generate_app.py.
"""

import os
import sys
import re
import logging
import urllib.request
import urllib.error
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

try:
    from icalendar import Calendar
except ImportError:
    print("ERROR: icalendar no instalado. Ejecuta: pip install icalendar")
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

BASE_DIR    = Path(__file__).parent
EXCEL_PATH  = BASE_DIR / 'PM_ESTUDIO_MASTER_COMPLETO.xlsx'
SHEET_NAME  = 'AUSENCIAS'
DRY_RUN     = os.environ.get('BIZNEO_DRY_RUN', '0') == '1'
LOG_LEVEL   = os.environ.get('BIZNEO_LOG_LEVEL', 'INFO')

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger('bizneo_sync')

# ── Semanas del Master Gantt  ─────────────────────────────────────────────────
# 14 semanas: 12 OCT 2026 → 11 ENE 2027
# Actualizar cuando cambie el horizonte del Gantt.
MASTER_WEEKS = [
    ("12 OCT", date(2026, 10, 12)),
    ("19 OCT", date(2026, 10, 19)),
    ("26 OCT", date(2026, 10, 26)),
    ("2 NOV",  date(2026, 11,  2)),
    ("9 NOV",  date(2026, 11,  9)),
    ("16 NOV", date(2026, 11, 16)),
    ("23 NOV", date(2026, 11, 23)),
    ("30 NOV", date(2026, 11, 30)),
    ("7 DIC",  date(2026, 12,  7)),
    ("14 DIC", date(2026, 12, 14)),
    ("21 DIC", date(2026, 12, 21)),
    ("28 DIC", date(2026, 12, 28)),
    ("4 ENE",  date(2027,  1,  4)),
    ("11 ENE", date(2027,  1, 11)),
]

# ── Mapeo nombres pila (Master) ↔ variantes en Bizneo ─────────────────────────
# Clave   : nombre de pila exacto usado en campo EQUIPO del Master Excel.
# Valor   : lista de strings que pueden aparecer como primer token del SUMMARY iCal.
# NOTA    : "Nela" está marcado como DUDOSO — confirmar nombre real en Bizneo.
# Completar con apellidos cuando el equipo tenga homónimos.
NAME_MAP = {
    "Sofía":    ["Sofía", "Sofia"],
    "Naiara":   ["Naiara"],
    "Marta":    ["Marta"],
    "Jesús":    ["Jesús", "Jesus"],
    "Olatz":    ["Olatz"],
    "Paula":    ["Paula"],
    "Sara":     ["Sara"],
    "Andrea":   ["Andrea"],
    "Nela":     ["Nela", "María Cristina"],
    "Cristina": ["Cristina"],
    "Ana":      ["Ana"],
    # Administración — se registran pero no generan alertas de proyectos
    "Mauro":    ["Mauro"],
    "Irene":    ["Irene"],
    "Susana":   ["Susana"],
}

# Personal de administración: sus ausencias se registran pero no generan
# alertas de cobertura de proyectos.
ADMIN_NAMES: set[str] = {"Mauro", "Irene", "Susana"}

# ══════════════════════════════════════════════════════════════════════════════
# ESTRUCTURA DE LA HOJA AUSENCIAS
# ══════════════════════════════════════════════════════════════════════════════

HEADERS = [
    # Identificación
    "UID_ICAL",           # A — clave primaria (nunca se duplica)
    # Persona
    "NOMBRE_PILA",        # B — nombre en Master o SIN_IDENTIFICAR
    "NOMBRE_BIZNEO",      # C — nombre completo extraído del iCal
    # Ausencia
    "TIPO_AUSENCIA",      # D — tipo (vacaciones, baja, festivo…)
    "FECHA_INICIO",       # E — fecha inicio inclusiva
    "FECHA_FIN",          # F — fecha fin inclusiva (DTEND-1d en all-day)
    "HORA_INICIO",        # G — HH:MM o "" si día completo
    "HORA_FIN",           # H — HH:MM o "" si día completo
    "DIA_COMPLETO",       # I — SI / NO
    # Planificación
    "SEMANAS_AFECTADAS",  # J — "12 OCT, 19 OCT" calculado desde MASTER_WEEKS
    "NUM_SEMANAS",        # K — número de semanas afectadas
    # Estado y control
    "ESTADO",             # L — CONFIRMADA / CANCELADA / SIN_IDENTIFICAR
    "ES_ADMIN",           # M — SI / NO (no genera alertas de cobertura)
    # Trazabilidad
    "SYNC_FECHA",         # N — último momento de sincronización
    "BIZNEO_MODIFIED",    # O — LAST-MODIFIED del evento iCal
    "PRIMERA_VEZ",        # P — primera vez que se procesó este UID
    "NOTAS",              # Q — observaciones (motivo SIN_IDENTIFICAR, etc.)
]

COL = {h: i + 1 for i, h in enumerate(HEADERS)}   # header → nº columna (1-based)

# ── Estilos ───────────────────────────────────────────────────────────────────
HDR_FILL  = PatternFill("solid", fgColor="1F3864")
HDR_FONT  = Font(name="Arial", bold=True, color="FFFFFF", size=10)
HDR_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
DAT_ALIGN = Alignment(horizontal="left", vertical="center")

STATUS_FILL = {
    "CONFIRMADA":      PatternFill("solid", fgColor="E8F5E9"),
    "CANCELADA":       PatternFill("solid", fgColor="F5F5F5"),
    "SIN_IDENTIFICAR": PatternFill("solid", fgColor="FFF9C4"),
}
STATUS_COLOR = {
    "CONFIRMADA":      "1B5E20",
    "CANCELADA":       "9E9E9E",
    "SIN_IDENTIFICAR": "E65100",
}
COL_WIDTHS = {
    "UID_ICAL": 38, "NOMBRE_PILA": 14, "NOMBRE_BIZNEO": 24,
    "TIPO_AUSENCIA": 22, "FECHA_INICIO": 13, "FECHA_FIN": 13,
    "HORA_INICIO": 10, "HORA_FIN": 10, "DIA_COMPLETO": 12,
    "SEMANAS_AFECTADAS": 40, "NUM_SEMANAS": 11, "ESTADO": 18,
    "ES_ADMIN": 9, "SYNC_FECHA": 18, "BIZNEO_MODIFIED": 18,
    "PRIMERA_VEZ": 18, "NOTAS": 42,
}

# ══════════════════════════════════════════════════════════════════════════════
# UTILIDADES iCAL
# ══════════════════════════════════════════════════════════════════════════════

def _to_date(val) -> date | None:
    if val is None:
        return None
    dt = getattr(val, 'dt', val)
    if isinstance(dt, datetime):
        return dt.date()
    if isinstance(dt, date):
        return dt
    return None

def _to_dt(val) -> datetime | None:
    if val is None:
        return None
    dt = getattr(val, 'dt', val)
    if isinstance(dt, datetime):
        if dt.tzinfo:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    if isinstance(dt, date):
        return datetime(dt.year, dt.month, dt.day)
    return None

def _is_allday(component) -> bool:
    dtstart = component.get('DTSTART')
    if dtstart is None:
        return True
    dt = getattr(dtstart, 'dt', dtstart)
    return isinstance(dt, date) and not isinstance(dt, datetime)

def _fix_dtend(component) -> date | None:
    """DTEND en eventos all-day es exclusivo; devuelve la fecha fin INCLUSIVA."""
    dtend = _to_date(component.get('DTEND'))
    if dtend and _is_allday(component):
        return dtend - timedelta(days=1)
    return dtend

def _times(component) -> tuple[str, str]:
    if _is_allday(component):
        return '', ''
    hi = _to_dt(component.get('DTSTART'))
    hf = _to_dt(component.get('DTEND'))
    return (hi.strftime('%H:%M') if hi else ''), (hf.strftime('%H:%M') if hf else '')

def calc_semanas(fi: date | None, ff: date | None) -> tuple[str, int]:
    """Calcula etiquetas de semanas del Master cubiertas por el rango [fi, ff]."""
    if fi is None or ff is None:
        return '', 0
    hits = [lbl for lbl, w0 in MASTER_WEEKS if fi <= w0 + timedelta(days=6) and ff >= w0]
    return ', '.join(hits), len(hits)

def extract_name_type(summary: str) -> tuple[str, str]:
    """
    Extrae nombre_bizneo y tipo_ausencia del SUMMARY.
    Bizneo usa el formato: "TipoAusencia - NOMBRE APELLIDOS"
    Ejemplo: "Vacaciones🏖️ - OLATZ MANDIOLA SOLOGAISTUA"
    """
    if not summary:
        return '', ''
    parts = re.split(r'\s*[-–—]\s*', summary.strip(), maxsplit=1)
    if len(parts) == 2:
        # Formato estándar Bizneo: tipo primero, nombre después
        tipo   = parts[0].strip()
        nombre = parts[1].strip()
    else:
        # Sin separador: el SUMMARY completo se trata como nombre, tipo desconocido
        nombre = parts[0].strip()
        tipo   = ''
    return nombre, tipo

def match_pila(nombre_bizneo: str) -> str:
    """
    Busca el nombre de pila del Master que corresponde al nombre Bizneo.
    Compara únicamente el primer token del nombre.
    Devuelve 'SIN_IDENTIFICAR' si no hay coincidencia exacta; nunca supone.
    """
    if not nombre_bizneo:
        return 'SIN_IDENTIFICAR'
    first = nombre_bizneo.split()[0] if nombre_bizneo.split() else ''
    for pila, variantes in NAME_MAP.items():
        for v in variantes:
            if v.lower() == first.lower() or v.lower() == nombre_bizneo.lower():
                return pila
    return 'SIN_IDENTIFICAR'

# ══════════════════════════════════════════════════════════════════════════════
# DESCARGA Y PARSEO
# ══════════════════════════════════════════════════════════════════════════════

def download_ical(url: str) -> bytes | None:
    """Descarga el iCal. La URL nunca aparece en logs. None = error."""
    log.info("Descargando calendario Bizneo…")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'pombo-bizneo-sync/1.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        log.info(f"Descarga OK — {len(data):,} bytes")
        return data
    except urllib.error.URLError as e:
        log.error(f"Error de red: {e.reason}")
    except Exception as e:
        log.error(f"Error inesperado al descargar: {type(e).__name__}: {e}")
    return None

def parse_ical(data: bytes) -> list[dict] | None:
    """Parsea el iCal. None = error de parsing."""
    try:
        cal = Calendar.from_ical(data)
    except Exception as e:
        log.error(f"Error parseando iCal: {e}")
        return None

    events = []
    for comp in cal.walk():
        if comp.name != 'VEVENT':
            continue
        uid = str(comp.get('UID', '')).strip()
        if not uid:
            log.warning("VEVENT sin UID — ignorado")
            continue

        summary       = str(comp.get('SUMMARY', ''))
        nombre_biz, tipo = extract_name_type(summary)
        nombre_pila   = match_pila(nombre_biz)
        dtstart       = _to_date(comp.get('DTSTART'))
        fecha_fin     = _fix_dtend(comp) if _is_allday(comp) else _to_date(comp.get('DTEND'))
        hi, hf        = _times(comp)
        sem_str, n_sem = calc_semanas(dtstart, fecha_fin)
        last_mod      = _to_dt(comp.get('LAST-MODIFIED'))
        es_admin      = 'SI' if nombre_pila in ADMIN_NAMES else 'NO'
        estado        = 'SIN_IDENTIFICAR' if nombre_pila == 'SIN_IDENTIFICAR' else 'CONFIRMADA'
        nota          = (f'Nombre no reconocido en NAME_MAP: {nombre_biz!r}'
                         if nombre_pila == 'SIN_IDENTIFICAR' else '')

        events.append({
            'UID_ICAL':          uid,
            'NOMBRE_PILA':       nombre_pila,
            'NOMBRE_BIZNEO':     nombre_biz,
            'TIPO_AUSENCIA':     tipo,
            'FECHA_INICIO':      dtstart,
            'FECHA_FIN':         fecha_fin,
            'HORA_INICIO':       hi,
            'HORA_FIN':          hf,
            'DIA_COMPLETO':      'SI' if _is_allday(comp) else 'NO',
            'SEMANAS_AFECTADAS': sem_str,
            'NUM_SEMANAS':       n_sem,
            'ESTADO':            estado,
            'ES_ADMIN':          es_admin,
            'BIZNEO_MODIFIED':   last_mod,
            'NOTAS':             nota,
        })

    log.info(f"Eventos parseados: {len(events)}")
    return events

# ══════════════════════════════════════════════════════════════════════════════
# GESTIÓN DE LA HOJA AUSENCIAS
# ══════════════════════════════════════════════════════════════════════════════

def ensure_sheet(wb: openpyxl.Workbook):
    """Crea la hoja AUSENCIAS al final del libro si no existe."""
    if SHEET_NAME in wb.sheetnames:
        return wb[SHEET_NAME]

    log.info(f"Creando hoja '{SHEET_NAME}'…")
    ws = wb.create_sheet(SHEET_NAME)

    for i, h in enumerate(HEADERS, 1):
        c = ws.cell(row=1, column=i, value=h)
        c.font, c.fill, c.alignment = HDR_FONT, HDR_FILL, HDR_ALIGN

    for h, w in COL_WIDTHS.items():
        ws.column_dimensions[get_column_letter(COL[h])].width = w

    ws.row_dimensions[1].height = 30
    ws.freeze_panes = 'A2'
    return ws

def load_existing(ws) -> dict[str, int]:
    """Devuelve {uid: row_number} con todos los registros existentes."""
    result = {}
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row,
                             min_col=COL['UID_ICAL'], max_col=COL['UID_ICAL']):
        uid_val = row[0].value
        if uid_val:
            result[str(uid_val).strip()] = row[0].row
    return result

def _write_row(ws, row_num: int, ev: dict, now: datetime, primera_vez: datetime):
    estado = ev.get('ESTADO', 'CONFIRMADA')
    fill   = STATUS_FILL.get(estado, PatternFill())
    fcolor = STATUS_COLOR.get(estado, "000000")
    values = [
        ev['UID_ICAL'], ev['NOMBRE_PILA'], ev['NOMBRE_BIZNEO'],
        ev['TIPO_AUSENCIA'], ev['FECHA_INICIO'], ev['FECHA_FIN'],
        ev['HORA_INICIO'], ev['HORA_FIN'], ev['DIA_COMPLETO'],
        ev['SEMANAS_AFECTADAS'], ev['NUM_SEMANAS'], estado,
        ev['ES_ADMIN'], now, ev['BIZNEO_MODIFIED'], primera_vez, ev['NOTAS'],
    ]
    for col, val in enumerate(values, 1):
        cell = ws.cell(row=row_num, column=col, value=val)
        cell.font      = Font(name="Arial", size=9, color=fcolor)
        cell.fill      = fill
        cell.alignment = DAT_ALIGN
        if isinstance(val, date) and not isinstance(val, datetime):
            cell.number_format = 'DD/MM/YYYY'
        elif isinstance(val, datetime):
            cell.number_format = 'DD/MM/YYYY HH:MM'

def _cancel_row(ws, row_num: int, now: datetime):
    """Marca la fila como CANCELADA sin borrar datos históricos."""
    ws.cell(row=row_num, column=COL['ESTADO']).value    = 'CANCELADA'
    ws.cell(row=row_num, column=COL['SYNC_FECHA']).value = now
    fill   = STATUS_FILL['CANCELADA']
    fcolor = STATUS_COLOR['CANCELADA']
    for col in range(1, len(HEADERS) + 1):
        cell = ws.cell(row=row_num, column=col)
        cell.fill = fill
        cell.font = Font(name="Arial", size=9, color=fcolor)

# ══════════════════════════════════════════════════════════════════════════════
# LÓGICA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def sync(excel_path: Path = EXCEL_PATH) -> dict:
    """
    Ejecuta la sincronización completa.
    Devuelve dict con estadísticas: nuevos, actualizados, cancelados,
    sin_identificar, sin_cambios, error.
    """
    stats = dict(nuevos=0, actualizados=0, cancelados=0,
                 sin_identificar=0, sin_cambios=0, error=None)

    # 1 — URL desde secreto de entorno (nunca hardcodeada)
    url = os.environ.get('BIZNEO_ICAL_URL')
    if not url:
        stats['error'] = 'BIZNEO_ICAL_URL no definida en el entorno'
        log.error(stats['error'])
        return stats

    # 2 — Descarga; si falla → preservar datos existentes
    raw = download_ical(url)
    if raw is None:
        stats['error'] = 'Fallo de descarga — datos existentes conservados sin cambios'
        return stats

    # 3 — Parsing; si falla → preservar datos existentes
    new_events = parse_ical(raw)
    if new_events is None:
        stats['error'] = 'Fallo de parsing — datos existentes conservados sin cambios'
        return stats

    # 4 — Cargar Excel
    if not excel_path.exists():
        stats['error'] = f'Excel no encontrado: {excel_path}'
        log.error(stats['error'])
        return stats

    wb = openpyxl.load_workbook(excel_path)
    ws = ensure_sheet(wb)

    existing  = load_existing(ws)          # {uid → row_num}
    new_uids  = {e['UID_ICAL'] for e in new_events}
    now       = datetime.now().replace(microsecond=0)

    # 5 — Cancelar eventos que desaparecieron del iCal (sync válida)
    for uid, row_num in existing.items():
        if uid not in new_uids:
            prev = ws.cell(row=row_num, column=COL['ESTADO']).value
            if prev != 'CANCELADA':
                _cancel_row(ws, row_num, now)
                stats['cancelados'] += 1
                log.info(f"  CANCELADA uid …{uid[-12:]}")

    # 6 — Insertar / actualizar
    next_row = (ws.max_row + 1) if ws.max_row and ws.max_row >= 2 else 2

    for ev in new_events:
        uid = ev['UID_ICAL']
        if ev['NOMBRE_PILA'] == 'SIN_IDENTIFICAR':
            stats['sin_identificar'] += 1

        if uid in existing:
            row_num = existing[uid]
            # Solo actualizar si LAST-MODIFIED es más reciente
            stored = ws.cell(row=row_num, column=COL['BIZNEO_MODIFIED']).value
            fresh  = ev.get('BIZNEO_MODIFIED')
            if fresh and stored and isinstance(stored, datetime):
                if fresh <= stored:
                    stats['sin_cambios'] += 1
                    continue
            pv = ws.cell(row=row_num, column=COL['PRIMERA_VEZ']).value
            _write_row(ws, row_num, ev, now, pv if isinstance(pv, datetime) else now)
            stats['actualizados'] += 1
        else:
            _write_row(ws, next_row, ev, now, primera_vez=now)
            next_row += 1
            stats['nuevos'] += 1

    # 7 — Guardar (a menos que sea dry-run)
    if DRY_RUN:
        log.info("DRY RUN — no se guarda el Excel")
    else:
        wb.save(excel_path)
        log.info(f"Excel guardado: {excel_path}")

    log.info(
        f"Sync completada → nuevos:{stats['nuevos']} "
        f"actualizados:{stats['actualizados']} cancelados:{stats['cancelados']} "
        f"sin_id:{stats['sin_identificar']} sin_cambios:{stats['sin_cambios']}"
    )
    return stats


# ══════════════════════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    result = sync()
    if result.get('error'):
        print(f"\n✗ {result['error']}")
        sys.exit(1)
    print(f"\n✓ Sync completada")
    print(f"  Nuevos:          {result['nuevos']}")
    print(f"  Actualizados:    {result['actualizados']}")
    print(f"  Cancelados:      {result['cancelados']}")
    print(f"  Sin identificar: {result['sin_identificar']}")
    print(f"  Sin cambios:     {result['sin_cambios']}")
