# -*- coding: utf-8 -*-
"""Seguimiento SENAMHI: Prioridades 100 dias (MINAM) y Acciones prioritarias FEN 2026.

Lee las dos matrices directamente desde Drive (cada direccion actualiza su fila
ahi) y muestra el tablero. La evolucion semanal sale de las instantaneas de
snapshot.py.

    streamlit run app.py
"""
from __future__ import annotations

import hmac

import streamlit as st

import vista100
import vistafen
from comun import CSS, b64
from datos import DIA_100, ESTADOS, INICIO_GOBIERNO, cargar, secreto

st.set_page_config(page_title="Seguimiento 100 días y FEN · SENAMHI", page_icon="assets/logo_senamhi.png",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)
LOGO, LOGO_MINAM = b64("assets/logo_senamhi.png"), b64("assets/logo_minam.png")


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


@st.cache_data(ttl=300, show_spinner="Leyendo las matrices…")
def datos():
    return cargar()


D = datos()
hoy = D["hoy"]
dia = (hoy - INICIO_GOBIERNO).days + 1
faltan = (DIA_100 - hoy).days

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown(f'<div class="logo-caja"><img src="data:image/png;base64,{LOGO}" width="100%"></div>', unsafe_allow_html=True)
    st.markdown("### Filtros · 100 días")
    filtros = {"estado": st.multiselect("Estado actual", ESTADOS, placeholder="Todos"),
               "prioridad": st.multiselect("Prioridad (MINAM)", ["Alta", "Media", "Baja"], placeholder="Todas"),
               "nino": st.toggle("Solo relacionadas con El Niño")}
    st.divider()
    for etq, sec in (("Abrir la matriz 100 días (Drive)", "MATRIZ_100DIAS_URL"), ("Abrir la matriz FEN (Drive)", "MATRIZ_FEN_URL")):
        if secreto(sec):
            st.link_button(etq, secreto(sec), icon=":material/edit:", width="stretch")
    if st.button("Actualizar datos", icon=":material/refresh:", width="stretch"):
        st.cache_data.clear()
        st.rerun()
    st.caption(f"Leído el {D['leido']:%d/%m/%Y %H:%M} (hora de Lima). "
               + ("Fuente: archivos de Drive; se vuelven a leer cada 5 minutos." if D["fuente100"] == "drive"
                  else "Fuente: copia local de las matrices."))
    st.caption(f"Gobierno desde el {INICIO_GOBIERNO:%d/%m/%Y}. Día 100: {DIA_100:%d/%m/%Y}.")

# ---------------------------------------------------------------- cabecera
c1, c2, c3 = st.columns([1.1, 4.2, 1.4])
with c1:
    st.markdown(f'<img src="data:image/png;base64,{LOGO}" width="100%" style="max-width:200px">', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="titulo"><h1>Seguimiento de prioridades · SENAMHI</h1>'
                '<p>Prioridades de los primeros 100 días y acciones prioritarias en el marco del FEN 2026.</p></div>',
                unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="dia"><div class="n">Día {dia}</div><div class="t">de 100 · '
                f'{"faltan " + str(faltan) + " días" if faltan >= 0 else "plazo cumplido"}</div>'
                f'<div class="barra"><div style="width:{min(max(dia, 0), 100)}%"></div></div></div>',
                unsafe_allow_html=True)
for aviso in D["avisos"]:
    st.warning(aviso, icon=":material/cloud_off:")

# ----------------------------------------------------------------- pestañas
t100, tfen = st.tabs([f"Prioridades 100 días · {len(D['m100'])} actividades",
                      f"Acciones prioritarias FEN 2026 · {len(D['fen'])} acciones"])
with t100:
    vista100.render(D, filtros)
with tfen:
    vistafen.render(D)

st.markdown("---")
f1, f2 = st.columns([5, 1])
f1.caption(f"SENAMHI · Dirección de Meteorología, Clima y Ambiente Atmosférico · Datos al {hoy:%d/%m/%Y}. "
           "Fuentes: Matriz de Prioridades 100 días del Sector Ambiente (MINAM) y Matriz de acciones prioritarias "
           "en el marco del FEN · SENAMHI 2026, ambas en Drive.")
f2.markdown(f'<img src="data:image/png;base64,{LOGO_MINAM}" width="100%" style="max-width:150px;opacity:.85">',
            unsafe_allow_html=True)
