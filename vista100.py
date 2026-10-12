# -*- coding: utf-8 -*-
"""Pestana 1: Prioridades de los primeros 100 dias (matriz MINAM)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comun import (AMARILLO, AZUL, COLOR_ESTADO, COLOR_SIT, GRIS_TXT, MESES_ES, barras_avance, dona_estado,
                   etiqueta, evolucion, excel, fecha, fecha_corta, fig_base, grafico, kpi, pct, por_direccion)
from datos import DIA_100, ESTADOS, INICIO_GOBIERNO, NOMBRE_DIR


def render(D: dict, filtros: dict) -> None:
    calc, hist, hoy = D["m100"], D["hist100"], D["hoy"]
    dirs = ["Todas"] + sorted(calc["Dirección"].dropna().unique())
    cnt = calc["Dirección"].value_counts()
    sel_dir = st.pills("Dirección", dirs, default="Todas", label_visibility="collapsed", key="dir100",
                       format_func=lambda d: "Todas las direcciones" if d == "Todas" else f"{d} · {cnt.get(d, 0)}")
    v = calc.copy()
    if sel_dir and sel_dir != "Todas":
        v = v[v["Dirección"] == sel_dir]
        st.caption(NOMBRE_DIR.get(sel_dir, ""))
    if filtros["estado"]:
        v = v[v["Estado actual"].isin(filtros["estado"])]
    if filtros["prioridad"]:
        v = v[v["Prioridad (MINAM)"].isin(filtros["prioridad"])]
    if filtros["nino"]:
        v = v[v["Relacionada con El Niño"] == "Sí"]
    v = v.reset_index(drop=True)
    if v.empty:
        st.info("No hay actividades con esos filtros.")
        return
    ant = v["Fecha anterior"].dropna().iloc[0] if v["Fecha anterior"].notna().any() else None

    # ---------------------------------------------------------------- KPIs
    k = st.columns(6)
    kpi(k[0], "Actividades", len(v), f"{int((v['Prioridad (MINAM)'] == 'Alta').sum())} de prioridad alta")
    kpi(k[1], "Avance promedio", pct(v["Avance (%)"].mean()), "según la matriz MINAM")
    kpi(k[2], "Completadas", int((v["Situación de plazo"] == "Completada").sum()), "avance al 100 %", COLOR_ESTADO["Completado"])
    kpi(k[3], "En proceso", int((v["Estado actual"] == "En proceso").sum()), "según la dirección", COLOR_ESTADO["En proceso"])
    venc = int((v["Situación de plazo"] == "Fecha límite vencida").sum())
    kpi(k[4], "Con fecha límite vencida", venc, "y avance menor a 100 %", COLOR_SIT["Fecha límite vencida"] if venc else AZUL)
    camb = int(v["Cambió"].sum())
    kpi(k[5], "Actualizadas esta semana", f"{camb} / {len(v)}",
        f"respecto al {fecha(ant)}" if ant else "sin corte anterior", AMARILLO if camb < len(v) else AZUL)
    st.markdown("")

    # ------------------------------------------------- avance + estado
    a, b = st.columns([3, 1.3])
    with a:
        etq = v["ID"].str.replace("SENAMHI-", "") + "  " + v["Nombre corto"].astype(str)
        grafico(barras_avance(v, etq, "% de avance por actividad (color = estado actual)",
                              ["Estado actual", "Fecha límite", "Producto", "Meta", "Unidad"]),
                alto=max(400, 34 * len(v) + 120))
    with b:
        dona_estado(v, ESTADOS, "Estado actual (lo declara cada dirección)")
        p = v["Prioridad (MINAM)"].value_counts()
        st.markdown("**Prioridad según la matriz MINAM:** " + " · ".join(f"{k} {int(n)}" for k, n in p.items()))
        st.markdown(f"**Relacionadas con El Niño (propuesta):** {int((v['Relacionada con El Niño'] == 'Sí').sum())}")

    # ------------------------------------------------------------ Gantt
    st.markdown("### Plazos: cuándo empieza y cuándo vence cada actividad")
    g = v.dropna(subset=["Fecha límite"]).copy()
    g["ini"] = [pd.Timestamp(x) if x else pd.Timestamp(INICIO_GOBIERNO) for x in g["Fecha inicio"]]
    g["lim"] = [pd.Timestamp(x) for x in g["Fecha límite"]]
    g = g.sort_values(["lim", "ID"], ascending=[False, False])
    MS_DIA = 86_400_000
    fig = go.Figure()
    for _, r in g.iterrows():
        y = r["ID"].replace("SENAMHI-", "") + "  " + str(r["Nombre corto"])[:52]
        col = COLOR_SIT.get(r["Situación de plazo"], "#B0BEC5")
        dur = max((r["lim"] - r["ini"]).days, 1)
        fig.add_bar(y=[y], x=[dur * MS_DIA], base=[r["ini"]], orientation="h", width=0.62, showlegend=False,
                    marker=dict(color=col, opacity=0.28, line=dict(width=0)),
                    hovertemplate=(f"<b>{r['Nombre corto']}</b><br>Inicio: {fecha(r['ini'])}<br>"
                                   f"Fecha límite: {fecha(r['lim'])}<br>Avance: {pct(r['Avance (%)'])}<br>"
                                   f"{r['Situación de plazo']}<extra></extra>"))
        av = min(max((r["Avance (%)"] if pd.notna(r["Avance (%)"]) else 0) / 100, 0), 1)
        if av > 0:
            fig.add_bar(y=[y], x=[dur * MS_DIA * av], base=[r["ini"]], orientation="h", width=0.62,
                        marker=dict(color=col, line=dict(width=0)), showlegend=False, hoverinfo="skip")
        fig.add_annotation(x=r["lim"], y=y, text=f"vence {fecha_corta(r['lim'])}", showarrow=False,
                           xanchor="left", xshift=8, font=dict(size=11, color=GRIS_TXT))
    for sit, col in COLOR_SIT.items():
        if sit in set(g["Situación de plazo"]):
            fig.add_bar(y=[None], x=[None], name=sit, marker=dict(color=col))
    fig.add_vline(x=pd.Timestamp(hoy), line=dict(color=AMARILLO, width=3))
    fig.add_annotation(x=pd.Timestamp(hoy), y=1.03, yref="paper", text=f"<b>hoy</b> {fecha_corta(hoy)}", showarrow=False,
                       font=dict(color="#9A7600", size=12))
    fig.add_vline(x=pd.Timestamp(DIA_100), line=dict(color=AZUL, width=2, dash="dash"))
    fig.add_annotation(x=pd.Timestamp(DIA_100), y=1.03, yref="paper", text=f"<b>día 100</b> {fecha_corta(DIA_100)}",
                       showarrow=False, font=dict(color=AZUL, size=12))
    if len(g):
        x0 = min(g["ini"].min(), pd.Timestamp(INICIO_GOBIERNO)) - pd.Timedelta(days=5)
        x1 = max(g["lim"].max(), pd.Timestamp(DIA_100)) + pd.Timedelta(days=28)
        meses = pd.date_range(x0.replace(day=1), x1, freq="MS")
        fig.update_layout(barmode="overlay",
                          xaxis=dict(type="date", range=[x0, x1], tickvals=meses,
                                     ticktext=[f"1 {MESES_ES[m.month - 1]}" for m in meses], gridcolor="#E3E8F0",
                                     tickfont=dict(size=12)),
                          yaxis=dict(tickfont=dict(size=12.5)),
                          title="La barra clara va del inicio a la fecha límite; la parte sólida es lo avanzado. Ordenadas por fecha límite.",
                          legend=dict(orientation="h", y=-0.12))
        st.plotly_chart(fig_base(fig, alto=max(380, 36 * len(g) + 130)), width="stretch")

    # ------------------------------------------------ evolucion y direcciones
    a, b = st.columns([3, 2])
    with a:
        evolucion(hist, v, "ID", hoy, "Avance semana a semana (color = dirección)")
    with b:
        por_direccion(v, "Avance promedio por dirección")

    # ------------------------------------------------------------- fichas
    st.markdown("### Ficha de cada actividad")
    st.caption("Todo lo que trae la matriz del MINAM, tal como la llena cada dirección.")
    for _, r in v.iterrows():
        est, sit = r["Estado actual"], r["Situación de plazo"]
        with st.expander(f"{r['ID'].replace('SENAMHI-', '')}  ·  {r['Nombre corto']}  ·  {pct(r['Avance (%)'])}"):
            st.markdown(etiqueta(est or "Sin estado", COLOR_ESTADO.get(est, "#B0BEC5")) + etiqueta(sit, COLOR_SIT.get(sit, "#B0BEC5"))
                        + etiqueta(f"Prioridad {r['Prioridad (MINAM)'] or '—'}", AZUL)
                        + (etiqueta("Relacionada con El Niño", "#E07A1F") if r["Relacionada con El Niño"] == "Sí" else "")
                        + (etiqueta("Actualizada esta semana", AMARILLO) if r["Cambió"] else ""),
                        unsafe_allow_html=True)
            cambio = (f"  (antes: {pct(r['Avance anterior'])} el {fecha(ant)})"
                      if ant and pd.notna(r["Avance anterior"]) and r["Avance anterior"] != r["Avance (%)"] else "")
            st.progress(min(int(r["Avance (%)"] if pd.notna(r["Avance (%)"]) else 0), 100),
                        text=f"Avance: {pct(r['Avance (%)'])}{cambio}")
            c1, c2 = st.columns(2)
            c1.markdown(f"**Actividad (matriz):** {r['Actividad']}  \n**Objetivo:** {r['Objetivo'] or '—'}  \n"
                        f"**Entregable:** {r['Producto']}  \n**Meta:** {r['Meta']} {r['Unidad']}  \n"
                        f"**Línea base:** {r['Línea base'] or '—'}  \n**Presupuesto estimado (S/):** {r['Presupuesto'] or '—'}")
            c2.markdown(f"**Dirección:** {NOMBRE_DIR.get(r['Dirección'], r['Dirección'])}  \n"
                        f"**Eje temático:** {r['Eje'] or '—'}  \n"
                        f"**Fechas:** {fecha(r['Fecha inicio'])} → {fecha(r['Fecha límite'])}"
                        f"{'  (' + str(int(r['Días para el límite'])) + ' días)' if pd.notna(r['Días para el límite']) else ''}  \n"
                        f"**Entidades de apoyo:** {r['Entidades de apoyo'] or '—'}")
            if r["Detalle"]:
                st.markdown(f"**Detalle del avance:** {r['Detalle']}")
            if r["Riesgos"]:
                st.markdown(f"**Riesgos / cuellos de botella:** {r['Riesgos']}")

    # ---------------------------------------------------------------- tablas
    t1, t2 = st.tabs(["Tabla de seguimiento", "Sin actualizar esta semana"])
    with t1:
        tabla = v[["ID", "Dirección", "Nombre corto", "Estado actual", "Avance (%)", "Avance anterior", "Prioridad (MINAM)",
                   "Meta", "Unidad", "Fecha límite", "Situación de plazo", "Detalle", "Riesgos"]]
        st.dataframe(tabla, width="stretch", hide_index=True, height=min(560, 40 * len(tabla) + 60),
                     column_config={
                         "Nombre corto": st.column_config.TextColumn("Actividad", width="large"),
                         "Avance (%)": st.column_config.ProgressColumn("Avance", format="%d %%", min_value=0, max_value=100),
                         "Avance anterior": st.column_config.NumberColumn("Corte anterior", format="%d %%"),
                         "Prioridad (MINAM)": "Prioridad",
                         "Fecha límite": st.column_config.DateColumn("Fecha límite", format="DD/MM/YYYY"),
                         "Detalle": st.column_config.TextColumn("Detalle del avance", width="medium")})
        st.download_button("Descargar en Excel", excel({"Seguimiento": tabla, "Historial": hist[hist["ID"].isin(v["ID"])]}),
                           f"prioridades_100dias_{hoy:%Y%m%d}.xlsx", icon=":material/download:", key="x100")
    with t2:
        sin = v[~v["Cambió"] & (v["Situación de plazo"] != "Completada")]
        if ant is None:
            st.info("Todavía no hay un corte anterior con qué comparar.")
        elif sin.empty:
            st.success("Todas las actividades en curso cambiaron su avance o estado desde el corte anterior.")
        else:
            st.markdown(f"**{len(sin)} actividades sin cambios en la matriz desde el {fecha(ant)}.** "
                        "Recordar a las direcciones que actualicen su fila en el archivo de Drive.")
            st.dataframe(sin[["Dirección", "ID", "Nombre corto", "Estado actual", "Avance (%)"]], width="stretch", hide_index=True,
                         column_config={"Nombre corto": st.column_config.TextColumn("Actividad", width="large")})
