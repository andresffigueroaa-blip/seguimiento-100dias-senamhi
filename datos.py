# -*- coding: utf-8 -*-
"""Datos del seguimiento: las dos matrices que viven en Drive.

1. PRIORIDADES 100 DIAS - SECTOR AMBIENTAL.xlsx (matriz MINAM): filas SENAMHI.
2. MATRIZ DE ACCIONES PRIORITARIAS EN EL MARCO DEL FEN SENAMHI 2026.xlsx.

Cada direccion actualiza su fila directamente en el archivo de Drive; la app lo
descarga (secrets MATRIZ_100DIAS_URL / MATRIZ_FEN_URL) y, si no puede, usa la
copia de datos/. La evolucion semanal sale de las instantaneas que guarda
snapshot.py en datos/historial_*.csv (una fila por actividad y fecha).
"""
from __future__ import annotations

import io
import os
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

AQUI = Path(__file__).resolve().parent
DATOS = AQUI / "datos"
LOCAL_100 = DATOS / "matriz_100dias.xlsx"
LOCAL_FEN = DATOS / "matriz_fen.xlsx"
HIST_100 = DATOS / "historial_100dias.csv"
HIST_FEN = DATOS / "historial_fen.csv"

INICIO_GOBIERNO = date(2026, 7, 28)
DIA_100 = date(2026, 11, 4)
ESTADOS = ["Sin iniciar", "En proceso", "Con riesgo / retraso", "Completado", "Reprogramado"]
ESTADOS_FEN = ["Sin iniciar", "En proceso", "En riesgo de retraso", "Implementado"]
SITUACIONES = ["Completada", "En plazo", "Por iniciar", "Fecha límite vencida", "Sin fecha límite"]
NOMBRE_DIR = {"DMCA": "Dirección de Meteorología, Clima y Ambiente Atmosférico",
              "DHI": "Dirección de Hidrología",
              "DSCA": "Dirección de Servicios, Cambio Climático y Agrometeorología",
              "DRD": "Dirección de Gestión de Redes de Observación y Datos"}
# ID fijo por actividad (palabras clave del texto de la matriz) y nombre corto (PPT 16/09/2026)
ACTIVIDADES = [
    ("SENAMHI-DHI-01", r"aforos", "Aforos de caudales en cuencas de Piura y Lima (alerta temprana)"),
    ("SENAMHI-DHI-02", r"estacional", "Pronósticos hidrológicos estacionales"),
    ("SENAMHI-DHI-03", r"\bares\b|inundaciones urbanas", "Portal ARES de inundaciones urbanas (Piura y Cusco)"),
    ("SENAMHI-DHI-04", r"pandora|madre de dios", "Plataforma PANDORA en la cuenca del río Madre de Dios"),
    ("SENAMHI-DRD-01", r"sensores", "Sensores automáticos en estaciones convencionales (vertiente occidental)"),
    ("SENAMHI-DSCA-01", r"sequia agricola|sinmosa", "Monitor Integrado de Sequías (ISPI), incluye sequía agrícola"),
    ("SENAMHI-DSCA-02", r"agrometeorologico", "Equipamiento agrometeorológico de precisión en estaciones MAP"),
    ("SENAMHI-DSCA-03", r"sorian", "Plataforma SORIAN con modelos de alta resolución"),
    ("SENAMHI-DMCA-01", r"vigilancia ambiental|calidad del aire", "Boletines de calidad del aire por incendios forestales en la Amazonía"),
    ("SENAMHI-DMCA-02", r"dobson|intercomparacion", "Campaña de intercomparación de espectrofotómetros Dobson 2026"),
    ("SENAMHI-DMCA-03", r"radar", "Productos de los radares meteorológicos de Piura e Ica"),
    ("SENAMHI-DMCA-04", r"monitor de sequias", "Monitor de Sequías del SENAMHI v1 (índices climáticos)"),
    ("SENAMHI-DMCA-05", r"ruta", "Ruta de Vigilancia El Niño (difusión en regiones expuestas)"),
]
PPT_NINO = {"SENAMHI-DRD-01", "SENAMHI-DSCA-03", "SENAMHI-DMCA-01", "SENAMHI-DMCA-05"}
SIGLA_DIR = [("hidrolog", "DHI"), ("redes", "DRD"), ("servicios", "DSCA"), ("meteorolog", "DMCA")]


def secreto(nombre: str) -> str:
    try:
        import streamlit as st
        if nombre in st.secrets:
            return str(st.secrets[nombre]).strip()
    except Exception:          # noqa: BLE001  (sin secrets.toml)
        pass
    return os.environ.get(nombre, "").strip()


# ------------------------------------------------------------------ ayudas
def plano(x) -> str:
    n = unicodedata.normalize("NFKD", str(x or ""))
    return re.sub(r"\s+", " ", "".join(c for c in n if not unicodedata.combining(c))).lower().strip()


def texto(v) -> str:
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else re.sub(r"\s+", " ", str(v)).strip()


def numero(v):
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "").replace("%", "").strip())
    except ValueError:
        return None


def normalizar_avance(v):
    x = numero(v)
    if x is None:
        return None
    return round(x * 100 if x <= 1 else x, 1)


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


def sigla(direccion: str) -> str:
    p = plano(direccion)
    return next((s for k, s in SIGLA_DIR if k in p), texto(direccion)[:6] or "—")


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


def ahora_lima() -> datetime:
    return datetime.now(ZoneInfo("America/Lima"))


# ---------------------------------------------------------------- descarga
def url_descarga(url: str) -> str:
    """Convierte un enlace de Drive / Google Sheets en un enlace de descarga del archivo."""
    u = url.strip()
    if "docs.google.com/spreadsheets" in u:
        m = re.search(r"/d/([\w-]+)", u)
        return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=xlsx" if m else u
    if "drive.google.com" in u:
        m = re.search(r"/d/([\w-]+)", u) or re.search(r"[?&]id=([\w-]+)", u)
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}" if m else u
    return u


def descargar(url: str) -> bytes:
    import requests
    r = requests.get(url_descarga(url), timeout=40)
    r.raise_for_status()
    if b"<html" in r.content[:300].lower():
        raise RuntimeError("Drive devolvió una página web, no el archivo: revisar que esté compartido "
                           "con «Cualquier persona con el enlace».")
    return r.content


def _hoja(contenido: bytes, nombre_contiene: str) -> list[list]:
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(contenido), data_only=True, read_only=True)
    ws = next((w for w in wb.worksheets if nombre_contiene in plano(w.title)), wb.worksheets[-1])
    return [list(r) for r in ws.iter_rows(values_only=True)]


def _columnas(fila_cab) -> dict[str, int]:
    """Indice de columna por encabezado (en minusculas y sin tildes)."""
    return {plano(v): i for i, v in enumerate(fila_cab) if v not in (None, "")}


def _col(cab: dict, *inicios) -> int | None:
    for ini in inicios:
        for k, i in cab.items():
            if k.startswith(ini):
                return i
    return None


def _celda(f, i):
    return f[i] if i is not None and i < len(f) else None


# ----------------------------------------------------- matriz 100 dias
def leer_matriz_100(contenido: bytes) -> pd.DataFrame:
    filas = _hoja(contenido, "prioridades")
    i_cab = next(i for i, f in enumerate(filas[:20]) if any("actividad" in plano(v) for v in f if v))
    cab = _columnas(filas[i_cab])
    c = {"responsable": _col(cab, "responsable"), "eje": _col(cab, "eje"), "objetivo": _col(cab, "objetivo"),
         "actividad": _col(cab, "actividad"), "producto": _col(cab, "producto"), "unidad": _col(cab, "unidad"),
         "meta": _col(cab, "meta"), "lbase": _col(cab, "linea base"), "presupuesto": _col(cab, "presupuesto"),
         "inicio": _col(cab, "fecha de inicio"), "limite": _col(cab, "fecha limite"), "prioridad": _col(cab, "nivel de"),
         "apoyo": _col(cab, "entidad"), "estado": _col(cab, "estado"), "avance": _col(cab, "% de avance", "% de"),
         "detalle": _col(cab, "detalle"), "riesgos": _col(cab, "riesgos")}
    i_id = _col(cab, "n° id", "n°", "id")
    out, usados = [], set()
    for f in filas[i_cab + 1:]:
        act = texto(_celda(f, c["actividad"]))
        resp = texto(_celda(f, c["responsable"]))
        # solo las filas cuyo N° ID dice SENAMHI (otras entidades del sector tienen direcciones con nombres parecidos)
        if "senamhi" not in plano(_celda(f, i_id)) or not act:
            continue
        pa = plano(act) + " " + plano(_celda(f, c["producto"]))
        id_ = next((i for i, rx, _ in ACTIVIDADES if re.search(rx, pa) and i not in usados), None)
        if id_ is None:
            s = sigla(resp)
            id_ = f"SENAMHI-{s}-{sum(1 for u in usados if f'-{s}-' in u) + 1:02d}"
        usados.add(id_)
        corto = next((n for i, _, n in ACTIVIDADES if i == id_), act[:80])
        nino = bool(re.search(r"\bnin[oa]\b|\bfen\b|enfen", pa)) or id_ in PPT_NINO
        out.append({
            "ID": id_, "Dirección": sigla(resp), "Nombre corto": corto, "Actividad": act,
            "Eje": texto(_celda(f, c["eje"])), "Objetivo": texto(_celda(f, c["objetivo"])),
            "Producto": texto(_celda(f, c["producto"])), "Unidad": texto(_celda(f, c["unidad"])),
            "Meta": _num_txt(_celda(f, c["meta"])), "Línea base": _num_txt(_celda(f, c["lbase"])),
            "Presupuesto": _num_txt(_celda(f, c["presupuesto"])),
            "Fecha inicio": fecha_valida(_celda(f, c["inicio"])), "Fecha límite": fecha_valida(_celda(f, c["limite"])),
            "Prioridad (MINAM)": texto(_celda(f, c["prioridad"])), "Entidades de apoyo": texto(_celda(f, c["apoyo"])),
            "Estado actual": _estado(_celda(f, c["estado"]), ESTADOS),
            "Avance (%)": normalizar_avance(_celda(f, c["avance"])),
            "Detalle": texto(_celda(f, c["detalle"])), "Riesgos": texto(_celda(f, c["riesgos"])),
            "Relacionada con El Niño": "Sí" if nino else "No"})
    df = pd.DataFrame(out)
    df["orden"] = df["ID"].map({i: k for k, (i, _, _) in enumerate(ACTIVIDADES)}).fillna(99)
    return df.sort_values(["orden", "ID"]).drop(columns="orden").reset_index(drop=True)


def _num_txt(v) -> str:
    x = numero(v)
    if x is None:
        return texto(v)
    return f"{x:,.0f}".replace(",", " ") if x == int(x) else f"{x:,.2f}".replace(",", " ")


def _estado(v, lista) -> str:
    p = plano(v)
    if not p:
        return ""
    if "implement" in p or "complet" in p or "culmin" in p:
        return "Implementado" if "Implementado" in lista else "Completado"
    if "riesgo" in p or "retras" in p:
        return "En riesgo de retraso" if "En riesgo de retraso" in lista else "Con riesgo / retraso"
    if "proces" in p:
        return "En proceso"
    if "reprogram" in p:
        return "Reprogramado"
    if "sin inic" in p or "no inic" in p:
        return "Sin iniciar"
    return texto(v)


# ----------------------------------------------------------- matriz FEN
def leer_matriz_fen(contenido: bytes) -> pd.DataFrame:
    filas = _hoja(contenido, "fen")
    i_cab = next(i for i, f in enumerate(filas[:20]) if any("actividad" in plano(v) for v in f if v))
    cab = _columnas(filas[i_cab])
    c = {"n": _col(cab, "n° id", "n°", "id"), "responsable": _col(cab, "responsable"), "eje": _col(cab, "eje"),
         "objetivo": _col(cab, "objetivo"), "actividad": _col(cab, "actividad"), "producto": _col(cab, "producto"),
         "unidad": _col(cab, "unidad"), "meta26": _col(cab, "meta al cierre", "meta 2026", "meta"),
         "meta27": _col(cab, "meta al 2027"), "ejecutada": _col(cab, "meta ejecutada"), "estado": _col(cab, "estado"),
         "detalle": _col(cab, "detalle"), "evidencia": _col(cab, "fotos", "evidencia", "link")}
    out = []
    for f in filas[i_cab + 1:]:
        act = texto(_celda(f, c["actividad"]))
        if not act:
            continue
        n = numero(_celda(f, c["n"]))
        meta, ejec = numero(_celda(f, c["meta26"])), numero(_celda(f, c["ejecutada"]))
        det = texto(_celda(f, c["detalle"]))
        estado = _estado(_celda(f, c["estado"]), ESTADOS_FEN)
        # Avance: meta ejecutada / meta 2026 si ambas son numeros; si no, el % que
        # la direccion escribio en el detalle; si no, 100 cuando declara Implementado.
        m = re.search(r"(\d{1,3})\s*%", det)
        if meta and ejec is not None:
            av, fuente = min(round(100 * ejec / meta, 1), 100.0), "meta ejecutada / meta 2026"
        elif m:
            av, fuente = min(float(m.group(1)), 100.0), "% escrito en el detalle"
        elif estado == "Implementado":
            av, fuente = 100.0, "estado Implementado"
        else:
            av, fuente = None, "sin dato"
        evid = texto(_celda(f, c["evidencia"]))
        prod = texto(_celda(f, c["producto"]))
        out.append({
            "N°": int(n) if n is not None else len(out) + 1, "Dirección": sigla(_celda(f, c["responsable"])),
            "Eje": texto(_celda(f, c["eje"])), "Objetivo": texto(_celda(f, c["objetivo"])),
            "Actividad": act, "Producto": prod, "Unidad": texto(_celda(f, c["unidad"])),
            "Meta 2026": _num_txt(_celda(f, c["meta26"])), "Meta 2027": _num_txt(_celda(f, c["meta27"])),
            "Meta ejecutada": _num_txt(_celda(f, c["ejecutada"])),
            "Estado actual": estado, "Avance (%)": av, "Avance (fuente)": fuente, "Detalle": det,
            "Evidencia": evid, "Enlaces": re.findall(r"https?://[^\s,;)]+", evid),
            "Nombre corto": (prod or act)[:70]})
    return pd.DataFrame(out)


# -------------------------------------------------------------- historial
def leer_historial(ruta: Path, clave: str) -> pd.DataFrame:
    if not ruta.exists():
        return pd.DataFrame({"Fecha": pd.Series(dtype="datetime64[ns]"), clave: pd.Series(dtype=object),
                             "Avance (%)": pd.Series(dtype=float), "Estado actual": pd.Series(dtype=object)})
    h = pd.read_csv(ruta, encoding="utf-8-sig")
    h["Fecha"] = pd.to_datetime(h["Fecha"], dayfirst=True, errors="coerce")
    h["Avance (%)"] = pd.to_numeric(h["Avance (%)"], errors="coerce")
    if clave == "N°":
        h[clave] = pd.to_numeric(h[clave], errors="coerce").astype("Int64")
    return h.dropna(subset=["Fecha"])


def guardar_instantanea(ruta: Path, df: pd.DataFrame, clave: str, fecha: date) -> int:
    """Agrega (o reemplaza) la lectura de `fecha` en el historial. Devuelve filas totales."""
    h = leer_historial(ruta, clave)
    h = h[h["Fecha"].dt.date != fecha]
    nuevo = df[[clave, "Avance (%)", "Estado actual"]].copy()
    nuevo.insert(0, "Fecha", pd.Timestamp(fecha))
    h = pd.concat([h, nuevo], ignore_index=True).sort_values(["Fecha", clave])
    h.assign(Fecha=h["Fecha"].dt.strftime("%d/%m/%Y")).to_csv(ruta, index=False, encoding="utf-8-sig")
    return len(h)


# ------------------------------------------------------------------ cargar
def _fuente(nombre_secreto: str, local: Path):
    url = secreto(nombre_secreto)
    if url:
        try:
            return descargar(url), "drive", ""
        except Exception as exc:      # noqa: BLE001
            return local.read_bytes(), "local", f"No se pudo leer el archivo de Drive ({str(exc)[:80]}): se muestra la copia local."
    return local.read_bytes(), "local", "Sin enlace al archivo de Drive: se muestra la copia local."


def cargar() -> dict:
    hoy = ahora_lima().date()
    b100, f100, a100 = _fuente("MATRIZ_100DIAS_URL", LOCAL_100)
    bfen, ffen, afen = _fuente("MATRIZ_FEN_URL", LOCAL_FEN)
    m100, fen = leer_matriz_100(b100), leer_matriz_fen(bfen)
    m100["Situación de plazo"] = [situacion_plazo(hoy, av if pd.notna(av) else None, ini, lim)
                                  for av, ini, lim in zip(m100["Avance (%)"], m100["Fecha inicio"], m100["Fecha límite"])]
    m100["Días para el límite"] = [(lim - hoy).days if lim else None for lim in m100["Fecha límite"]]
    h100, hfen = leer_historial(HIST_100, "ID"), leer_historial(HIST_FEN, "N°")
    # comparacion con la ultima instantanea anterior a hoy
    for df, h, clave in ((m100, h100, "ID"), (fen, hfen, "N°")):
        prev = h[h["Fecha"].dt.date < hoy]
        if len(prev):
            ult = prev[prev["Fecha"] == prev["Fecha"].max()].set_index(clave)
            df["Avance anterior"] = df[clave].map(ult["Avance (%)"])
            df["Estado anterior"] = df[clave].map(ult["Estado actual"])
            df["Fecha anterior"] = prev["Fecha"].max().date()
        else:
            df["Avance anterior"], df["Estado anterior"], df["Fecha anterior"] = None, None, None
        df["Cambió"] = [bool((pd.notna(a) and pd.notna(b) and a != b) or (pd.notna(ea) and str(e) != str(ea)))
                        for a, b, e, ea in zip(df["Avance (%)"], df["Avance anterior"], df["Estado actual"], df["Estado anterior"])]
    return {"m100": m100, "fen": fen, "hist100": h100, "histfen": hfen, "fuente100": f100, "fuentefen": ffen,
            "avisos": [a for a in (a100, afen) if a], "leido": ahora_lima(), "hoy": hoy}
