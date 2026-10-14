# -*- coding: utf-8 -*-
"""Pestana 2: Matriz de acciones prioritarias en el marco del FEN - SENAMHI 2026."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comun import (seccion_historia, tarjetas, AMARILLO, AZUL, COLOR_DIR, COLOR_ESTADO, barras_avance, dona_estado, etiqueta, evolucion, excel,
                   fecha, grafico, pct, por_direccion)
from datos import ESTADOS_FEN, NOMBRE_DIR


def render(D: dict) -> None:
    fen, hist, hoy = D["fen"], D["histfen"], D["hoy"]
    dirs = ["Todas"] + sorted(fen["Dirección"].dropna().unique())
    cnt = fen["Dirección"].value_counts()
    c1, c2 = st.columns([3, 2])
    sel_dir = c1.pills("Dirección", dirs, default="Todas", label_visibility="collapsed", key="dirfen",
                       format_func=lambda d: "Todas las direcciones" if d == "Todas" else f"{d} · {cnt.get(d, 0)}")
    f_est = c2.multiselect("Estado actual", ESTADOS_FEN, placeholder="Todos los estados", key="estfen",
                           label_visibility="collapsed")
    v = fen.copy()
    if sel_dir and sel_dir != "Todas":
        v = v[v["Dirección"] == sel_dir]
        st.caption(NOMBRE_DIR.get(sel_dir, ""))
    if f_est:
        v = v[v["Estado actual"].isin(f_est)]
    v = v.reset_index(drop=True)
    if v.empty:
        st.info("No hay acciones con esos filtros.")
        return
    ant = v["Fecha anterior"].dropna().iloc[0] if v["Fecha anterior"].notna().any() else None

    riesgo = int(v["Estado actual"].isin(["En riesgo de retraso", "Sin iniciar"]).sum())
    camb = int(v["Cambió"].sum())
    tarjetas([
        ("Acciones prioritarias", len(v), f"{v['Dirección'].nunique()} direcciones"),
        ("Implementadas", int((v["Estado actual"] == "Implementado").sum()), "según la dirección", COLOR_ESTADO["Implementado"]),
        ("En proceso", int((v["Estado actual"] == "En proceso").sum()), "según la dirección", COLOR_ESTADO["En proceso"]),
        ("En riesgo o sin iniciar", riesgo, "según la dirección", COLOR_ESTADO["En riesgo de retraso"] if riesgo else AZUL),
        ("Avance promedio", pct(v["Avance (%)"].mean()), f"{int(v['Avance (%)'].notna().sum())} con avance medible"),
        ("Actualizadas esta semana", f"{camb} / {len(v)}", f"respecto al {fecha(ant)}" if ant else "sin registro previo",
         AMARILLO if camb < len(v) else AZUL)])

    a, b = st.columns([3, 1.3])
    with a:
        etq = v["N°"].astype(str) + " · " + v["Dirección"] + "  " + v["Nombre corto"].astype(str)
        grafico(barras_avance(v, etq, "% de avance por acción (color = estado actual)",
                              ["Estado actual", "Meta 2026", "Meta ejecutada", "Avance (fuente)"]),
                alto=max(400, 34 * len(v) + 120))
        st.caption("El % sale de «Meta ejecutada / Meta 2026» cuando ambas son números; si no, del porcentaje que la "
                   "dirección escribió en el detalle; y 100 % cuando declara «Implementado». La fuente se ve al pasar el mouse.")
    with b:
        dona_estado(v, ESTADOS_FEN, "Estado actual (lo declara cada dirección)")
        g = v.groupby("Dirección").size()
        st.markdown("**Acciones por dirección:** " + " · ".join(f"{k} {int(n)}" for k, n in g.items()))

    a, b = st.columns([3, 2])
    with a:
        evolucion(hist, v, "Clave", D["ahora"], "Evolución del avance (color = dirección)")
    with b:
        por_direccion(v, "Avance promedio por dirección")

    seccion_historia(hist, v, "Clave", D["ahora"], "fen")

    st.markdown("### Metas: lo comprometido y lo ejecutado")
    tabla = v[["N°", "Dirección", "Nombre corto", "Unidad", "Meta 2026", "Meta 2027", "Meta ejecutada", "Estado actual", "Avance (%)"]]
    st.dataframe(tabla, width="stretch", hide_index=True, height=min(520, 40 * len(tabla) + 60),
                 column_config={"Nombre corto": st.column_config.TextColumn("Producto / entregable", width="large"),
                                "Avance (%)": st.column_config.ProgressColumn("Avance", format="%d %%", min_value=0, max_value=100)})

    st.markdown("### Ficha de cada acción")
    st.caption("Todo lo que trae la matriz FEN, tal como la llena cada dirección, con sus evidencias.")
    for _, r in v.iterrows():
        est = r["Estado actual"]
        with st.expander(f"{r['N°']}  ·  {r['Dirección']}  ·  {r['Nombre corto']}  ·  {pct(r['Avance (%)'])}"):
            st.markdown(etiqueta(est or "Sin estado", COLOR_ESTADO.get(est, "#B0BEC5"))
                        + etiqueta(r["Dirección"], COLOR_DIR.get(r["Dirección"], AZUL))
                        + (etiqueta("Actualizada esta semana", AMARILLO) if r["Cambió"] else ""), unsafe_allow_html=True)
            if pd.notna(r["Avance (%)"]):
                st.progress(min(int(r["Avance (%)"]), 100), text=f"Avance: {pct(r['Avance (%)'])} ({r['Avance (fuente)']})")
            c1, c2 = st.columns(2)
            c1.markdown(f"**Actividad:** {r['Actividad']}  \n**Objetivo:** {r['Objetivo'] or '—'}  \n"
                        f"**Producto / entregable:** {r['Producto'] or '—'}")
            c2.markdown(f"**Dirección:** {NOMBRE_DIR.get(r['Dirección'], r['Dirección'])}  \n**Eje temático:** {r['Eje'] or '—'}  \n"
                        f"**Unidad:** {r['Unidad'] or '—'}  \n**Meta 2026:** {r['Meta 2026'] or '—'} · "
                        f"**Meta 2027:** {r['Meta 2027'] or '—'} · **Ejecutada:** {r['Meta ejecutada'] or '—'}")
            if r["Detalle"]:
                st.markdown(f"**Detalle del avance:** {r['Detalle']}")
            if r["Evidencia"]:
                st.markdown(f"**Evidencia:** {r['Evidencia']}")
            if r["Enlaces"]:
                cols = st.columns(min(len(r["Enlaces"]), 4))
                for i, u in enumerate(r["Enlaces"][:4]):
                    cols[i].link_button(f"Abrir evidencia {i + 1}", u, icon=":material/open_in_new:", width="stretch")
    st.download_button("Descargar en Excel", excel({"FEN": v.drop(columns=["Enlaces"]), "Historial": hist[hist["Clave"].isin(v["Clave"])]}),
                       f"acciones_fen_{hoy:%Y%m%d}.xlsx", icon=":material/download:", key="xfen")
