#!/usr/bin/env python3
"""
update_gantt.py — APDS PM Estudio
Desplazamiento automático del horizonte Gantt al ciclo semanal actual.

Uso:
    python update_gantt.py              # aplica cambios en el Excel
    python update_gantt.py --dry-run    # muestra cambios sin modificar nada
    python update_gantt.py --date 2026-11-24   # simula ejecución en otra fecha

Comportamiento:
  1. Calcula el nuevo horizonte de 14 semanas desde el lunes de hoy.
  2. Lee el horizonte actual del Excel y compara.
  3. Si ya está actualizado, no hace nada.
  4. Remapea cada hito a su columna correcta según la fecha real del label.
  5. Archiva los hitos que caen fuera del nuevo horizonte en hoja HISTÓRICO.
  6. Detecta y reporta regresiones de fase sin corregirlas automáticamente.
  7. Actualiza las cabeceras de mes (fila 2) si existen.
  8. Guarda el Excel en-place. Git gestiona el histórico de versiones.

Restricciones:
  - NO modifica generate_app.py.
  - NO inventa hitos ni fechas.
  - NO elimina información: lo que no cabe en el horizonte va a HISTÓRICO.
  - NO corrige regresiones de fase: sólo las reporta.
"""

import argparse
import os
import sys
from copy import copy
from datetime import date, timedelta

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ─── Configuración ────────────────────────────────────────────────────────────
BASE            = os.path.dirname(os.path.abspath(__file__))
EXCEL_PATH      = os.path.join(BASE, 'PM_ESTUDIO_MASTER_COMPLETO.xlsx')
HORIZON_WEEKS   = 14
PLANNING_SHEETS = ['RESTAURANTES', 'VIVIENDA', 'HOTELES']

MESES    = {1:'ENE',2:'FEB',3:'MAR',4:'ABR',5:'MAY',6:'JUN',
            7:'JUL',8:'AGO',9:'SEP',10:'OCT',11:'NOV',12:'DIC'}
MESES_NUM = {v:k for k,v in MESES.items()}

# Fases en orden lógico (para detección de regresiones)
FASE_ORDER = ['PENDIENTE','PROY B','ANTEPROYECTO','ANT.PROY','PDTE LIC','PDTE LIC.',
              'LICITACIÓN','LIC.','PROY E','PROY DECO','ENTREGA','OBRA',
              'MONTAJE','REMATES','SEGUIM','ENTREGADO']

# ─── Helpers de fecha ─────────────────────────────────────────────────────────
def week_start(d: date) -> date:
    """Lunes de la semana de la fecha d."""
    return d - timedelta(days=d.weekday())

def label_fmt(d: date) -> str:
    """date → '16 NOV'  (sin cero en el día)."""
    return f"{d.day} {MESES[d.month]}"

def infer_dates_from_labels(labels: list, ref_date: date) -> list:
    """
    Convierte una lista ORDENADA de labels de semana a fechas reales.
    El año se infiere por orden: se incrementa cuando el mes retrocede
    (rollover de diciembre a enero).
    El primer mes se ancla al año de ref_date, con una tolerancia de ±6 meses.
    """
    result = []
    if not labels:
        return result

    year = ref_date.year
    first_mon = None
    for lbl in labels:
        parts = lbl.strip().split()
        if len(parts) == 2:
            m = MESES_NUM.get(parts[1].upper()[:3])
            if m:
                first_mon = m
                break
    if first_mon:
        if first_mon < ref_date.month - 6:
            year = ref_date.year + 1
        elif first_mon > ref_date.month + 6:
            year = ref_date.year - 1

    prev_mon = None
    for lbl in labels:
        parts = lbl.strip().split()
        if len(parts) != 2:
            result.append(None)
            continue
        try:
            day = int(parts[0])
            mon = MESES_NUM.get(parts[1].upper()[:3])
            if not mon:
                result.append(None)
                continue
            if prev_mon and mon < prev_mon:   # rollover DIC → ENE
                year += 1
            result.append(date(year, mon, day))
            prev_mon = mon
        except Exception:
            result.append(None)
    return result

def build_new_horizon(ref_date: date) -> list:
    """
    Construye los 14 (label, date) del nuevo horizonte empezando por
    el lunes de la semana de ref_date.
    """
    start = week_start(ref_date)
    return [(label_fmt(start + timedelta(weeks=i)),
             start + timedelta(weeks=i))
            for i in range(HORIZON_WEEKS)]

# ─── Lectura del Excel ────────────────────────────────────────────────────────
def _find_header_row(ws):
    """Fila (1-based) donde col2 == 'PROYECTO'."""
    for row in ws.iter_rows(min_row=1, max_row=15):
        for cell in row:
            if cell.value and str(cell.value).strip().upper() == 'PROYECTO':
                return cell.row
    return None

def _week_col_range(ws, header_row: int):
    """
    Devuelve (first_col_1based, [label, ...]) de las columnas de semana
    en la fila de cabecera.
    """
    first_col = None
    labels = []
    for cell in ws[header_row]:
        if cell.column <= 6:
            continue
        v = cell.value
        if v and any(ch.isdigit() for ch in str(v)):
            if first_col is None:
                first_col = cell.column
            labels.append(str(v).strip())
    return first_col, labels

def read_project_phases(ws, header_row: int, first_col: int,
                        old_dates: list) -> dict:
    """
    Lee todos los proyectos de la hoja y devuelve:
    { 'NOMBRE PROYECTO': { date: 'FASE', ... }, ... }
    """
    projects = {}
    for row in ws.iter_rows(min_row=header_row + 1, max_row=ws.max_row):
        proj_cell = row[1]   # columna B
        if not proj_cell.value:
            continue
        name = str(proj_cell.value).strip()
        if len(name) < 2 or name.startswith('▸') or name.startswith('──'):
            continue
        if name.upper() in ('VACACIONES', 'PROYECTO'):
            continue

        phases = {}
        for i, dt in enumerate(old_dates):
            col = first_col + i
            if col > ws.max_column:
                break
            cell = ws.cell(row=proj_cell.row, column=col)
            val  = cell.value
            if val and str(val).strip() not in ('', '—', 'None'):
                if dt:
                    phases[dt] = str(val).strip()
        if phases:
            projects[name] = phases
    return projects

# ─── Verificación de coherencia ───────────────────────────────────────────────
def check_regressions(name: str, phases: dict) -> list:
    """
    Detecta regresiones de fase en la secuencia ordenada por fecha.
    Devuelve lista de mensajes de alerta.
    """
    alerts = []
    ordered = sorted(phases.items())
    fase_order_upper = [f.upper() for f in FASE_ORDER]
    prev_rank, prev_lbl, prev_date = -1, None, None
    for dt, fase in ordered:
        rank = fase_order_upper.index(fase.upper()) if fase.upper() in fase_order_upper else -1
        if rank != -1 and prev_rank != -1 and rank < prev_rank:
            alerts.append(
                f"  ⚠ REGRESIÓN en {name}: "
                f"{label_fmt(prev_date)} '{prev_lbl}' → {label_fmt(dt)} '{fase}'"
            )
        if rank != -1:
            prev_rank, prev_lbl, prev_date = rank, fase, dt
    return alerts

# ─── Escritura del Excel ──────────────────────────────────────────────────────
_WEEK_FILL  = PatternFill('solid', fgColor='2F4F4F')
_WEEK_FONT  = Font(bold=True, color='FFFFFF', size=8, name='Calibri')
_WEEK_ALIGN = Alignment(horizontal='center', vertical='center', wrap_text=True)

def write_new_horizon(ws, header_row: int, first_col: int,
                      new_horizon: list,
                      all_projects: dict) -> dict:
    """
    Escribe las nuevas cabeceras de semana y reposiciona todos los hitos.
    Devuelve {nombre_proyecto: [mensajes_de_archivado]} para reporting.
    """
    archived = {}

    # 1. Cabeceras de semana
    for i, (lbl, _) in enumerate(new_horizon):
        cell = ws.cell(row=header_row, column=first_col + i)
        cell.value     = lbl
        cell.font      = _WEEK_FONT
        cell.fill      = _WEEK_FILL
        cell.alignment = _WEEK_ALIGN

    # 2. Limpiar columnas de semana en filas de datos
    for row in ws.iter_rows(min_row=header_row + 1, max_row=ws.max_row):
        proj_cell = row[1]
        if not proj_cell.value:
            continue
        for i in range(HORIZON_WEEKS):
            ws.cell(row=proj_cell.row, column=first_col + i).value = None

    # 3. Escribir hitos en posición correcta del nuevo horizonte
    new_date_to_col = {dt: first_col + i for i, (_, dt) in enumerate(new_horizon)}
    new_dates_set   = set(new_date_to_col.keys())

    for row in ws.iter_rows(min_row=header_row + 1, max_row=ws.max_row):
        proj_cell = row[1]
        if not proj_cell.value:
            continue
        name = str(proj_cell.value).strip()
        if name not in all_projects:
            continue

        archived_hits = []
        for dt, fase in sorted(all_projects[name].items()):
            if dt in new_date_to_col:
                col = new_date_to_col[dt]
                ws.cell(row=proj_cell.row, column=col).value = fase
            else:
                archived_hits.append((dt, fase))

        if archived_hits:
            archived[name] = [f"{label_fmt(d)}: {f}" for d, f in archived_hits]

    return archived

def update_historico(wb, archived_data: dict,
                     sheet_origins: dict):
    """
    Añade los hitos archivados a la hoja HISTÓRICO.
    La hoja se crea si no existe, con cabeceras: Fecha | Dept | Proyecto | Fase
    """
    if not archived_data:
        return

    if 'HISTÓRICO' not in wb.sheetnames:
        ws_h = wb.create_sheet('HISTÓRICO')
        ws_h.append(['Fecha', 'Departamento', 'Proyecto', 'Fase', 'Archivado en'])
        for cell in ws_h[1]:
            cell.font = Font(bold=True)
    else:
        ws_h = wb['HISTÓRICO']

    today_str = date.today().isoformat()
    for proj, entries in archived_data.items():
        dept = sheet_origins.get(proj, '—')
        for entry in entries:
            parts = entry.split(': ', 1)
            fecha = parts[0] if len(parts) == 2 else entry
            fase  = parts[1] if len(parts) == 2 else ''

            # Deduplicar
            already = False
            for row in ws_h.iter_rows(min_row=2, values_only=True):
                if row[0] == fecha and row[2] == proj and row[3] == fase:
                    already = True
                    break
            if not already:
                ws_h.append([fecha, dept, proj, fase, today_str])

# ─── Punto de entrada ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Actualiza el horizonte Gantt del Excel maestro')
    parser.add_argument('--dry-run', action='store_true',
                        help='Muestra cambios sin modificar el Excel')
    parser.add_argument('--date', default=None,
                        help='Fecha de referencia YYYY-MM-DD (default: hoy)')
    parser.add_argument('--excel', default=EXCEL_PATH,
                        help='Ruta al Excel (default: PM_ESTUDIO_MASTER_COMPLETO.xlsx)')
    args = parser.parse_args()

    ref_date = date.today()
    if args.date:
        ref_date = date.fromisoformat(args.date)

    excel_path = args.excel

    print(f"\n{'='*60}")
    print(f" update_gantt.py {'[DRY RUN] ' if args.dry_run else ''}— {ref_date.isoformat()}")
    print(f"{'='*60}\n")

    new_horizon = build_new_horizon(ref_date)
    new_labels  = [lbl for lbl, _ in new_horizon]
    print(f"Nuevo horizonte: {new_labels[0]} → {new_labels[-1]}")

    if not os.path.exists(excel_path):
        print(f"❌ Excel no encontrado: {excel_path}")
        sys.exit(1)

    wb = openpyxl.load_workbook(excel_path)
    print(f"Hojas: {wb.sheetnames}\n")

    all_archived_data = {}
    sheet_origins     = {}
    any_change        = False

    for sheet_name in PLANNING_SHEETS:
        if sheet_name not in wb.sheetnames:
            print(f"⚠ Hoja '{sheet_name}' no encontrada — omitiendo.\n")
            continue

        ws = wb[sheet_name]
        print(f"── {sheet_name} ──────────────────────────────")

        header_row = _find_header_row(ws)
        if header_row is None:
            print(f"  ⚠ No se encontró fila PROYECTO\n")
            continue

        first_col, old_labels = _week_col_range(ws, header_row)
        if not old_labels:
            print(f"  ⚠ No se encontraron columnas de semana\n")
            continue

        print(f"  Horizonte actual : {old_labels[0]} → {old_labels[-1]}")
        print(f"  Horizonte nuevo  : {new_labels[0]} → {new_labels[-1]}")

        if old_labels == new_labels:
            print(f"  ✓ Ya actualizado — sin cambios.\n")
            continue

        any_change = True

        old_dates = infer_dates_from_labels(old_labels, ref_date)

        print(f"\n  Rango actual  : {old_dates[0]} → {old_dates[-1]}")
        print(f"  Rango nuevo   : {new_horizon[0][1]} → {new_horizon[-1][1]}")

        new_dates_set = {dt for _, dt in new_horizon}
        old_dates_set = {d for d in old_dates if d}
        disappearing  = sorted(old_dates_set - new_dates_set)
        appearing     = sorted(new_dates_set - old_dates_set)

        if disappearing:
            print(f"\n  Semanas que se archivan ({len(disappearing)}): "
                  + ', '.join(label_fmt(d) for d in disappearing))
        if appearing:
            print(f"  Semanas nuevas ({len(appearing)}): "
                  + ', '.join(label_fmt(d) for d in appearing))

        all_projects = read_project_phases(ws, header_row, first_col, old_dates)
        print(f"\n  Proyectos con hitos: {len(all_projects)}")

        for pname in all_projects:
            sheet_origins[pname] = sheet_name

        regressions_found = False
        for pname, phases in all_projects.items():
            alerts = check_regressions(pname, phases)
            for a in alerts:
                print(a)
                regressions_found = True
        if not regressions_found:
            print(f"  ✓ Sin regresiones de fase detectadas")

        project_archived = {}
        for pname, phases in all_projects.items():
            hits_out = [(dt, f) for dt, f in phases.items()
                        if dt not in new_dates_set]
            if hits_out:
                project_archived[pname] = [f"{label_fmt(d)}: {f}" for d, f in sorted(hits_out)]
                all_archived_data[pname] = project_archived[pname]

        if project_archived:
            total = sum(len(v) for v in project_archived.values())
            print(f"\n  Hitos a archivar ({total}):")
            for pname, entries in project_archived.items():
                print(f"    {pname}: {', '.join(entries)}")

        if args.dry_run:
            print(f"\n  [DRY RUN] Resultado esperado por proyecto:")
            for pname, phases in all_projects.items():
                kept    = {dt: f for dt, f in phases.items() if dt in new_dates_set}
                not_in  = [dt for dt in phases if dt not in new_dates_set]
                kept_lbl = {label_fmt(dt): f for dt, f in sorted(kept.items())}
                if kept_lbl:
                    print(f"    {pname}: {kept_lbl}")
                if not_in:
                    print(f"      → archivados: {[label_fmt(d) for d in sorted(not_in)]}")
        else:
            write_new_horizon(ws, header_row, first_col, new_horizon, all_projects)

        print()

    if not any_change:
        print("✓ El horizonte del Gantt ya está actualizado. No se realizaron cambios.")
        return

    if args.dry_run:
        print("\n[DRY RUN] No se ha modificado el Excel.")
        print("          Ejecuta sin --dry-run para aplicar los cambios.")
        return

    if all_archived_data:
        total_arch = sum(len(v) for v in all_archived_data.values())
        print(f"Archivando {total_arch} hitos históricos en hoja HISTÓRICO...")
        update_historico(wb, all_archived_data, sheet_origins)

    wb.save(excel_path)
    print(f"\n✅ Excel actualizado: {excel_path}")
    print(f"   Horizonte Gantt: {new_labels[0]} → {new_labels[-1]}")

    if all_archived_data:
        total_arch = sum(len(v) for v in all_archived_data.values())
        print(f"   Hitos archivados en HISTÓRICO: {total_arch}")

if __name__ == '__main__':
    main()
