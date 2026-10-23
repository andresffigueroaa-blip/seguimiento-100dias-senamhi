# -*- coding: utf-8 -*-
"""Pestana 2: Matriz de acciones prioritarias en el marco del FEN - SENAMHI 2026."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comun import (seccion_historia, tarjetas, AMARILLO, AZUL, COLOR_DIR, COLOR_ESTADO, barras_avance, dona_estado, etiqueta, evolucion, excel,
                   fecha, grafico, pct, por_direccion)
from datos import ESTADOS_FEN, NOMBRE_DIR

# Periodo (pedido de la SVC del 23/10/2026): lo que se ejecuta en 2026 y lo programado para 2027.
# Las acciones «2026-2027» aparecen en los dos grupos.
EN_2026, EN_2027 = ["2026", "2026-2027"], ["2027", "2026-2027"]


def render(D: dict) -> None:
    fen, hist, hoy = D["fen"], D["histfen"], D["hoy"]
    n26, n27 = int(fen["Periodo"].isin(EN_2026).sum()), int(fen["Periodo"].isin(EN_2027).sum())
    periodo = st.pills("Periodo", ["2026", "2027"], default="2026", key="perfen", label_visibility="collapsed",
                       format_func=lambda p: f"En ejecución 2026 · {n26}" if p == "2026" else f"Programadas para el 2027 · {n27}") or "2026"
    fen = fen[fen["Periodo"].isin(EN_2026 if periodo == "2026" else EN_2027)].reset_index(drop=True)
    if periodo == "2027":
        st.markdown("### Acciones programadas para el 2027")
        st.caption("Lo que las direcciones proyectan atender el próximo año. Las que ya empezaron en 2026 y continúan aparecen también en "
                   "«En ejecución 2026».")
    dirs = ["Todas"] + sorted(fen["Dirección"].dropna().unique())
    cnt = fen["Dirección"].value_counts()
    c1, c2 = st.columns([3, 2])
    sel_dir = c1.pills("Dirección", dirs, default="Todas", label_visibility="collapsed", key="dirfen",
                       format_func=lambda d: "Todas las direcciones" if d == "Todas" else f"{d} · {cnt.get(d, 0)}")
    f_est = c2.multiselect("Estado actual", ESTADOS_FEN + (["Programada"] if periodo == "2027" else []), placeholder="Todos los estados",
                           key="estfen", label_visibility="collapsed")
    agrs = list(fen["Agrupación"].value_counts().index)
    sel_agr = st.pills("Agrupación temática (100 días de gobierno)", agrs, selection_mode="multi", key="agrfen",
                       format_func=lambda a: f"{a} · {int((fen['Agrupación'] == a).sum())}")
    v = fen.copy()
    if sel_agr:
        v = v[v["Agrupación"].isin(sel_agr)]
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

    if periodo == "2027":
        _programadas_2027(v, hist, hoy)
        return

    riesgo = int(v["Estado actual"].isin(["En riesgo de retraso", "Sin iniciar"]).sum())
    camb = int(v["Cambió"].sum())
    tarjetas([
        ("Acciones prioritarias", len(v), f"{v['Dirección'].nunique()} direcciones"),
        ("Implementadas", int((v["Estado actual"] == "Implementado").sum()), "según la dirección", COLOR_ESTADO["Implementado"]),
        ("En proceso", int((v["Estado actual"] == "En proceso").sum()), "según la dirección", COLOR_ESTADO["En proceso"]),
        ("En riesgo o sin iniciar", riesgo, "según la dirección", COLOR_ESTADO["En riesgo de retraso"] if riesgo else AZUL),
        ("Avance operativo promedio", pct(v["Avance (%)"].mean()), "lo que reporta cada dirección"),
        ("Avance de la meta promedio", pct(v["Avance de la meta (%)"].mean()), "meta ejecutada / meta 2026"),
        ("Actualizadas esta semana", f"{camb} / {len(v)}", f"respecto al {fecha(ant)}" if ant else "sin registro previo",
         AMARILLO if camb < len(v) else AZUL)])

    st.markdown("### Por agrupación temática")
    cols = st.columns(max(1, v["Agrupación"].nunique()))
    for col, (agr, g) in zip(cols, v.groupby("Agrupación", sort=False)):
        with col.container(border=True):
            st.markdown(f"**{agr}**")
            # cifras en HTML: st.metric cortaba «100 %» en «10…» cuando la tarjeta es angosta
            cifras = [("Acciones", len(g)), ("Avance operativo", pct(g["Avance (%)"].mean())),
                      ("Implementadas", int((g["Estado actual"] == "Implementado").sum()))]
            st.markdown('<div style="display:flex;gap:14px;flex-wrap:wrap;margin:2px 0 8px 0">' + "".join(
                f'<div style="min-width:70px"><div style="font-size:.8rem;color:#5B6B8A">{t}</div>'
                f'<div style="font-size:1.7rem;font-weight:700;line-height:1.1;white-space:nowrap">{v_}</div></div>'
                for t, v_ in cifras) + "</div>", unsafe_allow_html=True)
            st.progress(min(int(g["Avance (%)"].fillna(0).mean()), 100))
            st.caption(" · ".join(f"{d} {n}" for d, n in g["Dirección"].value_counts().items()))

    a, b = st.columns([3, 1.3])
    with a:
        etq = v["N°"].astype(str) + " · " + v["Dirección"] + "  " + v["Nombre corto"].astype(str)
        grafico(barras_avance(v, etq, "% de avance por acción (color = estado actual)",
                              ["Agrupación", "Estado actual", "Avance de la meta (%)", "Meta 2026", "Meta ejecutada", "Fecha de reporte"]),
                alto=max(400, 34 * len(v) + 120))
        st.caption("La barra es el «avance operativo de las labores de implementación» que cada dirección reporta cada "
                   "semana. El avance de la meta (meta ejecutada / meta 2026) solo marca 0 % o 100 % cuando la meta es una "
                   "unidad, por eso se muestra aparte, en la tabla de metas y al pasar el mouse.")
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
    tabla = v[["N°", "Dirección", "Agrupación", "Nombre corto", "Unidad", "Meta 2026", "Meta 2027", "Meta ejecutada", "Avance de la meta (%)",
               "Avance (%)", "Fecha de reporte", "Estado actual", "Periodo"]]
    st.dataframe(tabla, width="stretch", hide_index=True, height=min(520, 40 * len(tabla) + 60),
                 column_config={"Nombre corto": st.column_config.TextColumn("Producto / entregable", width="large"),
                                "Avance de la meta (%)": st.column_config.ProgressColumn("Avance de la meta (C/A)", format="%d %%",
                                                                                         min_value=0, max_value=100),
                                "Avance (%)": st.column_config.ProgressColumn("Avance operativo", format="%d %%", min_value=0, max_value=100)})

    fichas(v)
    st.download_button("Descargar en Excel", excel({"FEN": v.drop(columns=["Enlaces"]), "Historial": hist[hist["Clave"].isin(v["Clave"])]}),
                       f"acciones_fen_{hoy:%Y%m%d}.xlsx", icon=":material/download:", key="xfen")


def _programadas_2027(v: pd.DataFrame, hist: pd.DataFrame, hoy) -> None:
    """Vista del periodo 2027: cuantas, de quien y con que meta; sin avance operativo (aun no empiezan)."""
    cont = int((v["Periodo"] == "2026-2027").sum())
    con_fecha = int((v["Fecha prevista"] != "").sum())
    con_meta = int((v["Meta 2027"] != "").sum())
    tarjetas([
        ("Acciones programadas", len(v), f"{v['Dirección'].nunique()} direcciones"),
        ("Nuevas en 2027", len(v) - cont, "empiezan el próximo año", AZUL),
        ("Continúan de 2026", cont, "ya están en ejecución", COLOR_ESTADO["En proceso"]),
        ("Con meta 2027 definida", con_meta, f"de {len(v)}", COLOR_ESTADO["Implementado"] if con_meta == len(v) else AMARILLO),
        ("Con fecha prevista", con_fecha, f"de {len(v)}", COLOR_ESTADO["Implementado"] if con_fecha == len(v) else AMARILLO)])
    if (v["Periodo (fuente)"].str.startswith("regla")).any():
        st.info("La matriz aún no tiene la columna «Periodo de ejecución». Mientras tanto, solo cuenta como programada para 2027 la acción "
                "que tiene meta 2027 y no tiene meta 2026. Cuando las direcciones llenen esa columna (2026, 2027 o 2026-2027), manda lo que escriban.")

    st.markdown("### Por agrupación temática")
    cols = st.columns(max(1, v["Agrupación"].nunique()))
    for col, (agr, g) in zip(cols, v.groupby("Agrupación", sort=False)):
        with col.container(border=True):
            st.markdown(f"**{agr}**")
            cifras = [("Acciones", len(g)), ("Nuevas 2027", int((g["Periodo"] == "2027").sum())), ("Continúan", int((g["Periodo"] == "2026-2027").sum()))]
            st.markdown('<div style="display:flex;gap:14px;flex-wrap:wrap;margin:2px 0 8px 0">' + "".join(
                f'<div style="min-width:70px"><div style="font-size:.8rem;color:#5B6B8A">{t}</div>'
                f'<div style="font-size:1.7rem;font-weight:700;line-height:1.1;white-space:nowrap">{v_}</div></div>'
                for t, v_ in cifras) + "</div>", unsafe_allow_html=True)
            st.caption(" · ".join(f"{d} {n}" for d, n in g["Dirección"].value_counts().items()))

    st.markdown("### Qué se programa para el 2027")
    tabla = v[["N°", "Dirección", "Agrupación", "Nombre corto", "Unidad", "Meta 2027", "Fecha prevista", "Periodo", "Estado actual"]]
    st.dataframe(tabla, width="stretch", hide_index=True, height=min(520, 40 * len(tabla) + 60),
                 column_config={"Nombre corto": st.column_config.TextColumn("Producto / entregable", width="large"),
                                "Periodo": st.column_config.TextColumn("Periodo", help="2027: empieza el próximo año · 2026-2027: ya está en ejecución y continúa")})
    fichas(v)
    st.download_button("Descargar en Excel", excel({"FEN 2027": v.drop(columns=["Enlaces"]), "Historial": hist[hist["Clave"].isin(v["Clave"])]}),
                       f"acciones_fen_2027_{hoy:%Y%m%d}.xlsx", icon=":material/download:", key="xfen27")


def fichas(v: pd.DataFrame) -> None:
    st.markdown("### Ficha de cada acción")
    st.caption("Todo lo que trae la matriz FEN, tal como la llena cada dirección, con sus evidencias.")
    for _, r in v.iterrows():
        est = r["Estado actual"]
        with st.expander(f"{r['N°']}  ·  {r['Dirección']}  ·  {r['Nombre corto']}  ·  {pct(r['Avance (%)'])}"):
            st.markdown(etiqueta(est or "Sin estado", COLOR_ESTADO.get(est, "#B0BEC5"))
                        + etiqueta(r["Dirección"], COLOR_DIR.get(r["Dirección"], AZUL))
                        + (etiqueta("Continúa en 2027", "#6E5BAA") if r["Periodo"] == "2026-2027" else "")
                        + (etiqueta("Programada para 2027", "#6E5BAA") if r["Periodo"] == "2027" else "")
                        + (etiqueta("Actualizada esta semana", AMARILLO) if r["Cambió"] else ""), unsafe_allow_html=True)
            if pd.notna(r["Avance (%)"]):
                st.progress(min(int(r["Avance (%)"]), 100), text=f"Avance: {pct(r['Avance (%)'])} ({r['Avance (fuente)']})")
            st.caption(f"Avance de la meta (ejecutada / meta 2026): {pct(r['Avance de la meta (%)'])} · "
                       f"Fecha de reporte: {r['Fecha de reporte'] or '—'}")
            c1, c2 = st.columns(2)
            c1.markdown(f"**Actividad:** {r['Actividad']}  \n**Objetivo:** {r['Objetivo'] or '—'}  \n"
                        f"**Producto / entregable:** {r['Producto'] or '—'}")
            c2.markdown(f"**Dirección:** {NOMBRE_DIR.get(r['Dirección'], r['Dirección'])}  \n**Agrupación temática:** {r['Agrupación']}  \n**Eje temático:** {r['Eje'] or '—'}  \n"
                        f"**Unidad:** {r['Unidad'] or '—'}  \n**Meta 2026:** {r['Meta 2026'] or '—'} · "
                        f"**Meta 2027:** {r['Meta 2027'] or '—'} · **Ejecutada:** {r['Meta ejecutada'] or '—'}  \n"
                        f"**Periodo:** {r['Periodo']} ({r['Periodo (fuente)']}) · **Fecha prevista:** {r['Fecha prevista'] or '—'}")
            if r["Detalle"]:
                st.markdown(f"**Detalle del avance:** {r['Detalle']}")
            if r["Evidencia"]:
                st.markdown(f"**Evidencia:** {r['Evidencia']}")
            if r["Enlaces"]:
                cols = st.columns(min(len(r["Enlaces"]), 4))
                for i, u in enumerate(r["Enlaces"][:4]):
                    cols[i].link_button(f"Abrir evidencia {i + 1}", u, icon=":material/open_in_new:", width="stretch")
