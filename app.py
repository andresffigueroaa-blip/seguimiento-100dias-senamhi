# -*- coding: utf-8 -*-
"""Seguimiento SENAMHI: matriz de acciones prioritarias 2026-2027 (metas de los 100 dias, 2026, 2027 y 2026-2027).

Lee la matriz directamente desde Drive (cada direccion actualiza su fila ahi) y muestra el tablero.
La evolucion semanal sale de las instantaneas de snapshot.py.

    streamlit run app.py
"""
from __future__ import annotations

import hmac
import importlib
import os
import sys
from pathlib import Path

import streamlit as st


def recargar_modulos_cambiados() -> None:
    """Streamlit Cloud baja los archivos de cada push, pero deja en memoria los módulos ya
    importados (datos, comun, vistas). Si alguno cambió, se sacan todos de memoria y los imports
    de abajo los cargan de nuevo: recargar solo el que cambió dejaba a las vistas con funciones
    viejas de comun (pasó con las barras de avance el 21/10/2026)."""
    vistos = getattr(sys, "_seg_mtimes", {})
    propios = _modulos_propios()
    if any(vistos.get(n) != t for n, t in propios.items()):
        for n in propios:
            del sys.modules[n]
        importlib.invalidate_caches()


def _modulos_propios() -> dict:
    base = os.path.normcase(str(Path(__file__).resolve().parent))
    out = {}
    for n, m in list(sys.modules.items()):
        f = getattr(m, "__file__", None)
        if n != "__main__" and f and os.path.normcase(os.path.abspath(f)).startswith(base):
            out[n] = os.path.getmtime(f) if os.path.exists(f) else None
    return out


recargar_modulos_cambiados()

import vistafen  # noqa: E402
from comun import CSS, b64  # noqa: E402
from datos import DIA_100, INICIO_GOBIERNO, cargar, secreto, url_matriz
sys._seg_mtimes = _modulos_propios()   # fechas de lo recién importado

st.set_page_config(page_title="Seguimiento de prioridades · SENAMHI", page_icon="assets/logo_senamhi.png",
                   layout="wide", initial_sidebar_state="collapsed")
st.markdown(CSS, unsafe_allow_html=True)
LOGO = b64("assets/logo_senamhi.png")


# ------------------------------------------------------------------ acceso
def acceso() -> None:
    clave = secreto("PASSWORD")
    if not clave or st.session_state.get("_ok"):
        return
    _, c, _ = st.columns([1, 1.1, 1])
    with c:
        st.markdown(f'<div class="logo-caja" style="text-align:center"><img src="data:image/png;base64,{LOGO}" width="260"></div>',
                    unsafe_allow_html=True)
        st.markdown("#### Seguimiento de prioridades · SENAMHI")
        with st.form("ingreso"):
            p = st.text_input("Clave de acceso", type="password")
            if st.form_submit_button("Entrar", type="primary"):
                if hmac.compare_digest(p.encode(), clave.encode()):
                    st.session_state["_ok"] = True
                    st.rerun()
                st.error("Clave incorrecta.")
    st.stop()


acceso()


@st.cache_data(ttl=300, show_spinner="Leyendo la matriz…")
def datos():
    return cargar()


D = datos()
hoy = D["hoy"]
dia = (hoy - INICIO_GOBIERNO).days + 1
faltan = (DIA_100 - hoy).days

# ---------------------------------------------------------------- cabecera (mismo estilo que el tablero DMCA)
st.markdown(f'<div class="cab"><img src="data:image/png;base64,{LOGO}">'
            '<div><div class="tit">Seguimiento de prioridades · SENAMHI</div>'
            f'<div class="sub">Matriz de acciones prioritarias 2026-2027 · {len(D["fen"])} acciones</div></div>'
            f'<div class="dia"><div class="n">Día {dia}</div><div class="t">de 100 · '
            f'{"faltan " + str(faltan) + " días" if faltan >= 0 else "plazo cumplido"}</div>'
            f'<div class="barra"><div style="width:{min(max(dia, 0), 100)}%"></div></div></div></div>',
            unsafe_allow_html=True)
for aviso in D["avisos"]:
    st.warning(aviso, icon=":material/cloud_off:")

# acceso directo a la hoja que alimenta el tablero (para actualizarla y comprobar que es esa)
b1, b2, b3 = st.columns([1.6, 1.2, 4])
b1.link_button("Abrir la matriz en Google Sheets", url_matriz(), icon=":material/table_view:", type="primary", width="stretch")
if b2.button("Actualizar datos", icon=":material/refresh:", width="stretch", key="act_arriba"):
    st.cache_data.clear()
    st.rerun()
b3.caption(f"Última lectura: {D['leido']:%d/%m/%Y %H:%M}"
           + ("" if D["fuentefen"] == "drive" else " · copia local, la hoja no respondió"))

vistafen.render(D)

st.markdown(f'<div class="pie">SENAMHI · Dirección de Meteorología, Clima y Ambiente Atmosférico · datos al {hoy:%d/%m/%Y} · '
            'fuente: matriz de acciones prioritarias 2026-2027 en Google Sheets</div>', unsafe_allow_html=True)
