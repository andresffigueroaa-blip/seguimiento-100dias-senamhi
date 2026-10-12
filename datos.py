# -*- coding: utf-8 -*-
"""Datos del seguimiento de 100 dias para la app.

Fuente principal: las pestanas Calculos, Historial e Hitos_RutaElNino del
Google Sheet, publicadas como CSV (URLs en st.secrets o variables de
entorno). Respaldo: el libro .xlsx de la carpeta datos/, recalculado aqui
con la misma logica de las formulas.
"""
from __future__ import annotations

import io
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
XLSX = AQUI / "datos" / "Seguimiento_100dias_SENAMHI.xlsx"
INICIO_GOBIERNO = date(2026, 7, 28)
DIA_100 = date(2026, 11, 4)
ESTADOS = ["Sin iniciar", "En proceso", "Con riesgo / retraso", "Completado", "Reprogramado"]
SITUACIONES = ["Completada", "En plazo", "Por iniciar", "Fecha límite vencida", "Sin fecha límite"]
NOMBRE_DIR = {"DMCA": "Dirección de Meteorología, Clima y Ambiente Atmosférico",
              "DHI": "Dirección de Hidrología",
              "DSCA": "Dirección de Servicios, Cambio Climático y Agrometeorología",
              "DRD": "Dirección de Gestión de Redes de Observación y Datos"}
COLS = ["ID", "Dirección", "Nombre corto", "Actividad", "Producto", "Unidad", "Meta", "Línea base",
        "Prioridad (MINAM)", "Relacionada con El Niño", "Estado actual", "Enlace responsable",
        "Fecha inicio", "Fecha límite", "Link entregable", "Alertas", "Último corte", "Avance (%)",
        "Acciones", "Día de gestión", "Días para el límite", "Situación de plazo",
        "Reportó esta semana", "Semanas sin reportar", "Hitos cumplidos", "Base (%)"]


def secreto(nombre: str) -> str:
    try:
        import streamlit as st
        if nombre in st.secrets:
            return str(st.secrets[nombre]).strip()
    except Exception:          # noqa: BLE001  (sin secrets.toml)
        pass
    return os.environ.get(nombre, "").strip()


# ------------------------------------------------------------ reglas
def normalizar_avance(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, str):
        t = v.strip().replace("%", "").replace(",", ".")
        if t in ("", "-"):
            return None
        try:
            v = float(t)
        except ValueError:
            return None
    v = float(v)
    return round(v * 100 if v <= 1 else v, 2)


def fecha_valida(v):
    if v is None or v == "" or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (datetime, pd.Timestamp)):
        d = v.date()
    elif isinstance(v, date):
        d = v
    else:
        d = pd.to_datetime(str(v), dayfirst=True, errors="coerce")
        if pd.isna(d):
            return None
        d = d.date()
    return d if d.year >= 2000 else None


def situacion_plazo(hoy, avance, inicio, limite):
    if avance is not None and avance >= 100:
        return "Completada"
    if limite is None:
        return "Sin fecha límite"
    if hoy > limite:
        return "Fecha límite vencida"
    if inicio is not None and hoy < inicio:
        return "Por iniciar"
    return "En plazo"


def proximo_corte(hoy: date) -> date:
    return hoy + pd.Timedelta(days=(4 - hoy.weekday()) % 7)


# ------------------------------------------------------- desde el Sheet
def _csv(url: str) -> pd.DataFrame:
    import requests
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return pd.read_csv(io.StringIO(r.content.decode("utf-8-sig")))   # Sheets publica en UTF-8


def desde_sheet():
    u1, u2 = secreto("SEG100_CALCULOS_CSV"), secreto("SEG100_HISTORIAL_CSV")
    if not (u1 and u2):
        return None
    calc, hist = _csv(u1), _csv(u2)
    calc = calc[calc["ID"].notna() & (calc["ID"].astype(str).str.strip() != "")].copy()
    hist = hist[hist["ID"].notna() & (hist["ID"].astype(str).str.strip() != "")].copy()
    for c in ("Fecha inicio", "Fecha límite", "Último corte"):
        calc[c] = pd.to_datetime(calc[c], dayfirst=True, errors="coerce")
    for c in ("Avance (%)", "Base (%)", "Semanas sin reportar", "Día de gestión", "Días para el límite"):
        calc[c] = pd.to_numeric(calc[c], errors="coerce")
    for c in COLS:
        if c not in calc.columns:
            calc[c] = ""
    for c in ("Meta", "Línea base"):
        calc[c] = calc[c].fillna("").astype(str).str.replace(r"\.0$", "", regex=True)
    hist["Fecha de corte"] = pd.to_datetime(hist["Fecha de corte"], dayfirst=True, errors="coerce")
    hist["Avance (%)"] = pd.to_numeric(hist["Avance (%)"], errors="coerce")
    # Ultimo corte y acciones: se toman del Historial (ultimo reporte semanal con
    # dato), que es la fuente mas fiable; la formula de la hoja no es igual en
    # todas las versiones de Sheets.
    base = hist["Fecha de corte"].min()
    ult = (hist[hist["Avance (%)"].notna() & (hist["Fecha de corte"] > base)]
           .sort_values("Fecha de corte").groupby("ID").last())
    calc["Último corte"] = calc["ID"].map(ult["Fecha de corte"])
    calc["Acciones"] = calc["ID"].map(ult["Acciones"]).fillna("")
    # Avance: ultimo valor con dato en el Historial (incluida la base del 02/10).
    # La formula LOOKUP de la hoja no se recalcula igual en Sheets, asi que la app
    # no depende de ella; con esto el dashboard refleja lo escrito el mismo dia.
    todos = hist[hist["Avance (%)"].notna()].sort_values("Fecha de corte").groupby("ID").last()
    calc["Avance (%)"] = calc["ID"].map(todos["Avance (%)"]).fillna(calc["Base (%)"])
    hoy = datetime.now(ZoneInfo("America/Lima")).date()
    calc["Situación de plazo"] = [
        situacion_plazo(hoy, av if pd.notna(av) else None, fecha_valida(ini), fecha_valida(lim))
        for av, ini, lim in zip(calc["Avance (%)"], calc["Fecha inicio"], calc["Fecha límite"])]
    calc["Días para el límite"] = [(fecha_valida(lim) - hoy).days if fecha_valida(lim) else None
                                   for lim in calc["Fecha límite"]]
    u3 = secreto("SEG100_HITOS_CSV")
    hitos = _csv(u3) if u3 else pd.DataFrame()
    if len(hitos):
        hitos = hitos[hitos["Fecha"].notna()].copy()
        hitos["Fecha"] = pd.to_datetime(hitos["Fecha"], dayfirst=True, errors="coerce")
    return calc, hist, hitos


# --------------------------------------------------- desde el .xlsx local
def desde_xlsx(hoy: date | None = None):
    from openpyxl import load_workbook
    from zoneinfo import ZoneInfo
    hoy = hoy or datetime.now(ZoneInfo("America/Lima")).date()
    wb = load_workbook(XLSX)
    ws = wb["Seguimiento"]
    n_fijas = 17
    fechas = {j: ws.cell(1, j).value for j in range(n_fijas, ws.max_column + 1)
              if hasattr(ws.cell(1, j).value, "year")}
    fechas = {j: (f.date() if hasattr(f, "date") else f) for j, f in fechas.items()}
    corte = proximo_corte(hoy)
    calc, hist = [], []
    for r in range(3, ws.max_row + 1):
        id_ = ws.cell(r, 1).value
        if not id_:
            continue
        f = [ws.cell(r, j).value for j in range(1, n_fijas + 1)]
        (id_, dire, corto, act, prod, unidad, meta, lbase, prio, nino, fini, flim, estado,
         enlace, link, alertas, base) = f
        ini, lim, base = fecha_valida(fini), fecha_valida(flim), normalizar_avance(base)
        ult, av, acc, sin = None, base, "", 0
        for j, fc in fechas.items():
            if j == n_fijas:
                hist.append((id_, dire, corto, fc, base, "Avance inicial (matriz MINAM)"))
                continue
            v = normalizar_avance(ws.cell(r, j).value)
            hist.append((id_, dire, corto, fc, v, ws.cell(r, j + 1).value if v is not None else None))
            if v is not None:
                ult, av, acc = fc, v, ws.cell(r, j + 1).value or ""
            elif fc <= corte:
                sin += 1
        rep = any(ws.cell(r, j).value not in (None, "") for j, fc in fechas.items()
                  if j != n_fijas and fc == corte)
        calc.append({
            "ID": id_, "Dirección": dire, "Nombre corto": corto or "", "Actividad": act or "",
            "Producto": prod or "", "Unidad": unidad or "", "Meta": "" if meta is None else meta,
            "Línea base": "" if lbase is None else lbase, "Prioridad (MINAM)": prio or "",
            "Relacionada con El Niño": nino or "", "Estado actual": estado or "",
            "Enlace responsable": enlace or "", "Fecha inicio": pd.Timestamp(ini) if ini else pd.NaT,
            "Fecha límite": pd.Timestamp(lim) if lim else pd.NaT, "Link entregable": link or "",
            "Alertas": alertas or "", "Último corte": pd.Timestamp(ult) if ult else pd.NaT,
            "Avance (%)": av, "Acciones": acc, "Día de gestión": (hoy - INICIO_GOBIERNO).days + 1,
            "Días para el límite": (lim - hoy).days if lim else None,
            "Situación de plazo": situacion_plazo(hoy, av, ini, lim),
            "Reportó esta semana": "Sí" if rep else "No", "Semanas sin reportar": sin,
            "Hitos cumplidos": "", "Base (%)": base})
    h = pd.DataFrame(hist, columns=["ID", "Dirección", "Nombre corto", "Fecha de corte", "Avance (%)", "Acciones"])
    h["Fecha de corte"] = pd.to_datetime(h["Fecha de corte"])
    wh = wb["Hitos_RutaElNino"]
    hitos = pd.DataFrame([[wh.cell(r, j).value for j in range(1, 6)] for r in range(2, wh.max_row + 1)
                          if wh.cell(r, 1).value],
                         columns=["Fecha", "Evento / lugar", "Realizado (Sí/No)", "Observación", "Link evidencia"])
    hitos["Fecha"] = pd.to_datetime(hitos["Fecha"])
    df = pd.DataFrame(calc, columns=COLS)
    for c in ("Meta", "Línea base"):
        df[c] = df[c].map(lambda x: "" if x in ("", None) else (f"{x:g}" if isinstance(x, (int, float)) else str(x)))
    return df, h, hitos


def cargar():
    """(calculos, historial, hitos, fuente, aviso)."""
    try:
        r = desde_sheet()
        if r is not None:
            return (*r, "sheet", "")
        aviso = "Sin conexión al Google Sheet: se muestra la última copia local."
    except Exception as exc:          # noqa: BLE001
        aviso = f"No se pudo leer el Google Sheet ({str(exc)[:90]}): se muestra la última copia local."
    c, h, hi = desde_xlsx()
    return c, h, hi, "xlsx", aviso
