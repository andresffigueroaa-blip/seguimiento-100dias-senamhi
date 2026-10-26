# -*- coding: utf-8 -*-
"""Tablero de la matriz de acciones prioritarias SENAMHI 2026-2027 (una sola matriz desde el 26/10/2026).

Cada accion tiene un «Tipo de meta»: Meta 100 dias, Meta 2026, Meta 2027 o Meta 2026-2027. El tablero se
filtra por tipo de meta, direccion, eje tematico, agrupacion tematica y estado; usa el nombre corto en los
graficos y deja el nombre completo en la ficha de cada accion."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from comun import (AMARILLO, AZUL, COLOR_DIR, COLOR_ESTADO, COLOR_TIPO, EXPLICA_TIPO, GRIS_TXT, barras_avance, dona_estado, etiqueta,
                   evolucion, excel, fecha, fig_base, grafico, pct, por_direccion, seccion_historia, tarjetas)
from datos import ESTADOS_FEN, NOMBRE_DIR, TIPOS_META


def _pills(etq, opciones, key, fmt, multi=False, default=None):
    kw = dict(selection_mode="multi") if multi else dict(default=default)
    return st.pills(etq, opciones, key=key, format_func=fmt, label_visibility="collapsed" if default else "visible", **kw)


def render(D: dict) -> None:
    fen, hist, hoy = D["fen"], D["histfen"], D["hoy"]
    tipos = [t for t in TIPOS_META + ["Sin tipo"] if (fen["Tipo de meta"] == t).any()]
    n_tipo = fen["Tipo de meta"].value_counts()

    # ------------------------------------------------------------------ filtros
    sel_tipo = st.pills("Tipo de meta", ["Todas"] + tipos, default="Todas", key="tipofen", label_visibility="collapsed",
                        format_func=lambda t: f"Todas las metas · {len(fen)}" if t == "Todas" else f"{t} · {n_tipo.get(t, 0)}")
    v = fen if sel_tipo in (None, "Todas") else fen[fen["Tipo de meta"] == sel_tipo]
    if sel_tipo not in (None, "Todas"):
        st.markdown(f"### {sel_tipo}: {EXPLICA_TIPO.get(sel_tipo, '')}")
    c1, c2 = st.columns([3, 2])
    dirs = ["Todas"] + sorted(v["Dirección"].dropna().unique())
    cnt = v["Dirección"].value_counts()
    sel_dir = c1.pills("Dirección", dirs, default="Todas", label_visibility="collapsed", key="dirfen",
                       format_func=lambda d: "Todas las direcciones" if d == "Todas" else f"{d} · {cnt.get(d, 0)}")
    f_est = c2.multiselect("Estado actual", ESTADOS_FEN, placeholder="Todos los estados", key="estfen", label_visibility="collapsed")
    ejes = list(v["Eje corto"].value_counts().index)
    sel_eje = st.pills("Eje temático", ejes, selection_mode="multi", key="ejefen",
                       format_func=lambda e: f"{e} · {int((v['Eje corto'] == e).sum())}")
    agrs = [a for a in v["Agrupación"].value_counts().index if a != "Sin agrupación"]
    sel_agr = st.pills("Agrupación temática (100 días de gobierno)", agrs, selection_mode="multi", key="agrfen",
                       format_func=lambda a: f"{a} · {int((v['Agrupación'] == a).sum())}") if agrs else None
    if sel_dir and sel_dir != "Todas":
        v = v[v["Dirección"] == sel_dir]
        st.caption(NOMBRE_DIR.get(sel_dir, ""))
    if sel_eje:
        v = v[v["Eje corto"].isin(sel_eje)]
    if sel_agr:
        v = v[v["Agrupación"].isin(sel_agr)]
    if f_est:
        v = v[v["Estado actual"].isin(f_est)]
    v = v.reset_index(drop=True)
    if v.empty:
        st.info("No hay acciones con esos filtros.")
        return
    ant = v["Fecha anterior"].dropna().iloc[0] if v["Fecha anterior"].notna().any() else None

    # ------------------------------------------------------------------ cifras
    riesgo = int(v["Estado actual"].isin(["En riesgo de retraso", "Sin iniciar"]).sum())
    camb = int(v["Cambió"].sum())
    tarjetas([
        ("Acciones", len(v), f"{v['Dirección'].nunique()} direcciones · {v['Eje corto'].nunique()} ejes"),
        ("Implementadas", int((v["Estado actual"] == "Implementado").sum()), "según la dirección", COLOR_ESTADO["Implementado"]),
        ("En proceso", int((v["Estado actual"] == "En proceso").sum()), "según la dirección", COLOR_ESTADO["En proceso"]),
        ("En riesgo o sin iniciar", riesgo, "según la dirección", COLOR_ESTADO["En riesgo de retraso"] if riesgo else AZUL),
        ("Avance operativo promedio", pct(v["Avance (%)"].mean()), "lo que reporta cada dirección"),
        ("Avance de la meta promedio", pct(v["Avance de la meta (%)"].mean()), "meta ejecutada / meta del año"),
        ("Actualizadas esta semana", f"{camb} / {len(v)}", f"respecto al {fecha(ant)}" if ant else "sin registro previo",
         AMARILLO if camb < len(v) else AZUL)])

    # ------------------------------------------------------------------ por tipo de meta (siempre, para ver el conjunto)
    if sel_tipo in (None, "Todas"):
        st.markdown("### Por tipo de meta")
        cols = st.columns(len(tipos))
        for col, t in zip(cols, tipos):
            g = v[v["Tipo de meta"] == t]
            with col.container(border=True):
                st.markdown(f"**{etiqueta(t, COLOR_TIPO[t])}**", unsafe_allow_html=True)
                st.caption(EXPLICA_TIPO.get(t, ""))
                _cifras([("Acciones", len(g)), ("Avance", pct(g["Avance (%)"].mean()) if len(g) else "—"),
                         ("Implementadas", int((g["Estado actual"] == "Implementado").sum()))])
                st.progress(min(int(g["Avance (%)"].fillna(0).mean()) if len(g) else 0, 100))
                st.caption(" · ".join(f"{d} {n}" for d, n in g["Dirección"].value_counts().items()) or "sin acciones con estos filtros")

    # ------------------------------------------------------------------ mapa de acciones + estado
    a, b = st.columns([3, 1.3])
    with a:
        _mapa(v)
    with b:
        dona_estado(v, ESTADOS_FEN, "Estado actual (lo declara cada dirección)")
        g = v.groupby("Dirección").size()
        st.markdown("**Acciones por dirección:** " + " · ".join(f"{k} {int(n)}" for k, n in g.items()))

    # ------------------------------------------------------------------ avance por acción (nombre corto)
    etq = v["N°"].astype(str) + " · " + v["Dirección"] + " · " + v["Nombre corto"].astype(str)
    grafico(barras_avance(v, etq, "% de avance operativo por acción (color = estado actual)",
                          ["Tipo de meta", "Eje corto", "Meta 2026", "Meta 2027", "Meta ejecutada", "Avance de la meta (%)", "Fecha de reporte"]),
            alto=max(420, 34 * len(v) + 120))
    st.caption("La barra es el avance operativo que cada dirección reporta. El avance de la meta (ejecutada / meta del año) "
               "se ve al pasar el mouse y en la tabla de metas.")

    a, b = st.columns(2)
    with a:
        _por_eje(v)
    with b:
        por_direccion(v, "Avance promedio por dirección")

    evolucion(hist, v, "Clave", D["ahora"], "Evolución del avance (color = dirección)")
    seccion_historia(hist, v, "Clave", D["ahora"], "fen")

    # ------------------------------------------------------------------ metas
    st.markdown("### Metas: lo comprometido y lo ejecutado")
    st.caption("«—» en una meta significa que la acción no es de ese año.")
    tabla = v[["N°", "Dirección", "Tipo de meta", "Eje corto", "Nombre corto", "Unidad", "Meta 2026", "Meta 2027", "Meta ejecutada",
               "Avance de la meta (%)", "Avance (%)", "Fecha de reporte", "Estado actual"]]
    st.dataframe(tabla, width="stretch", hide_index=True, height=min(560, 40 * len(tabla) + 60),
                 column_config={"Nombre corto": st.column_config.TextColumn("Acción (nombre corto)", width="large"), "Eje corto": "Eje temático",
                                "Avance de la meta (%)": st.column_config.ProgressColumn("Avance de la meta (C/A)", format="%d %%", min_value=0, max_value=100),
                                "Avance (%)": st.column_config.ProgressColumn("Avance operativo", format="%d %%", min_value=0, max_value=100)})

    # ------------------------------------------------------------------ fichas
    st.markdown("### Ficha de cada acción")
    st.caption("Todo lo que trae la matriz, tal como la llena cada dirección, con el nombre completo y sus evidencias.")
    for _, r in v.iterrows():
        est = r["Estado actual"]
        with st.expander(f"{r['N°']}  ·  {r['Dirección']}  ·  {r['Nombre corto']}  ·  {pct(r['Avance (%)'])}"):
            st.markdown(etiqueta(r["Tipo de meta"], COLOR_TIPO.get(r["Tipo de meta"], "#B0BEC5"))
                        + etiqueta(est or "Sin estado", COLOR_ESTADO.get(est, "#B0BEC5"))
                        + etiqueta(r["Dirección"], COLOR_DIR.get(r["Dirección"], AZUL))
                        + (etiqueta("Actualizada esta semana", AMARILLO) if r["Cambió"] else ""), unsafe_allow_html=True)
            if pd.notna(r["Avance (%)"]):
                st.progress(min(int(r["Avance (%)"]), 100), text=f"Avance operativo: {pct(r['Avance (%)'])} ({r['Avance (fuente)']})")
            st.caption(f"Avance de la meta (ejecutada / meta del año): {pct(r['Avance de la meta (%)'])} · "
                       f"Fecha de reporte: {r['Fecha de reporte'] or '—'} · Tipo de meta según {r['Tipo (fuente)']}")
            c1, c2 = st.columns(2)
            c1.markdown(f"**Actividad:** {r['Actividad']}  \n**Objetivo:** {r['Objetivo'] or '—'}  \n"
                        f"**Producto / entregable:** {r['Producto'] or '—'}")
            c2.markdown(f"**Dirección:** {NOMBRE_DIR.get(r['Dirección'], r['Dirección'])}  \n**Eje temático:** {r['Eje'] or '—'}  \n"
                        f"**Agrupación temática:** {r['Agrupación']}  \n**Unidad:** {r['Unidad'] or '—'}  \n"
                        f"**Meta 2026:** {r['Meta 2026']} · **Meta 2027:** {r['Meta 2027']} · **Ejecutada:** {r['Meta ejecutada'] or '—'}"
                        + (f"  \n**Fecha prevista:** {r['Fecha prevista']}" if r["Fecha prevista"] else ""))
            if r["Detalle"]:
                st.markdown(f"**Detalle del avance:** {r['Detalle']}")
            if r["Evidencia"]:
                st.markdown(f"**Evidencia:** {r['Evidencia']}")
            if r["Enlaces"]:
                cols = st.columns(min(len(r["Enlaces"]), 4))
                for i, u in enumerate(r["Enlaces"][:4]):
                    cols[i].link_button(f"Abrir evidencia {i + 1}", u, icon=":material/open_in_new:", width="stretch")
    st.download_button("Descargar en Excel", excel({"Acciones": v.drop(columns=["Enlaces"]), "Historial": hist[hist["Clave"].isin(v["Clave"])]}),
                       f"acciones_prioritarias_{hoy:%Y%m%d}.xlsx", icon=":material/download:", key="xfen")


def _cifras(items: list[tuple]) -> None:
    # cifras en HTML: st.metric cortaba «100 %» en «10…» cuando la tarjeta es angosta
    st.markdown('<div style="display:flex;gap:14px;flex-wrap:wrap;margin:2px 0 8px 0">' + "".join(
        f'<div style="min-width:70px"><div style="font-size:.8rem;color:{GRIS_TXT}">{t}</div>'
        f'<div style="font-size:1.7rem;font-weight:700;line-height:1.1;white-space:nowrap">{x}</div></div>' for t, x in items)
        + "</div>", unsafe_allow_html=True)


def _mapa(v: pd.DataFrame) -> None:
    """Mapa de rectangulos: tipo de meta → eje tematico → accion (tamaño igual, color = avance). Clic para entrar."""
    d = v.assign(n=1, Avance=v["Avance (%)"].fillna(0), Nombre=v["Nombre corto"].astype(str).map(lambda t: t if len(t) <= 48 else t[:46] + "…"))
    fig = px.treemap(d, path=[px.Constant("Acciones prioritarias"), "Tipo de meta", "Eje corto", "Nombre"], values="n", color="Avance",
                     color_continuous_scale=[[0, "#E8EDF3"], [0.5, "#7FA6D9"], [1, "#2E7D32"]], range_color=[0, 100],
                     custom_data=["Dirección", "Estado actual", "Avance"], title="Acciones por tipo de meta y eje temático (color = avance)")
    fig.update_traces(hovertemplate="<b>%{label}</b><br>%{customdata[0]} · %{customdata[1]}<br>Avance: %{customdata[2]:.0f} %<extra></extra>",
                      textfont=dict(size=13), marker=dict(line=dict(color="white", width=2)), root_color="white")
    fig.update_layout(coloraxis_colorbar=dict(title="Avance", ticksuffix=" %", thickness=12, len=0.6))
    fig.update_traces(textfont=dict(size=13), insidetextfont=dict(size=12))
    grafico(fig, alto=max(420, 34 * len(v) + 120) if len(v) < 12 else 620, leyenda=False)
    st.caption("Clic en un tipo de meta o en un eje para acercarse; clic en el título superior para volver.")


def _por_eje(v: pd.DataFrame) -> None:
    d = (v.groupby("Eje corto").agg(Acciones=("Avance (%)", "size"), Avance=("Avance (%)", "mean"),
                                   Impl=("Estado actual", lambda s: int((s == "Implementado").sum()))).reset_index().sort_values("Avance"))
    fig = go.Figure(go.Bar(x=d["Avance"].fillna(0), y=d["Eje corto"], orientation="h", marker=dict(color=AZUL),
                           text=[f"{pct(a)}  ·  {int(n)} acc.  ·  {int(i)} impl." for a, n, i in zip(d["Avance"], d["Acciones"], d["Impl"])],
                           textposition="outside", textfont=dict(size=12), hovertemplate="%{y}: %{x:.0f} % promedio<extra></extra>"))
    fig.update_layout(title="Avance promedio por eje temático", xaxis=dict(range=[0, 175], visible=False), yaxis=dict(tickfont=dict(size=12.5)))
    grafico(fig, alto=max(300, 38 * len(d) + 110), leyenda=False)
