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

from comun import (AMARILLO, AZUL, COLOR_DIR, COLOR_ESTADO, COLOR_TIPO, EXPLICA_TIPO, GRIS_TXT, LINEA, TINTA, barras_avance, dona_estado,
                   etiqueta, evolucion, excel, fecha, fig_base, grafico, pct, por_direccion, seccion_historia, tarjetas)
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
        ("Implementadas", int((v["Estado actual"] == "Implementado").sum()), "", COLOR_ESTADO["Implementado"]),
        ("En proceso", int((v["Estado actual"] == "En proceso").sum()), "", COLOR_ESTADO["En proceso"]),
        ("En riesgo o sin iniciar", riesgo, "", COLOR_ESTADO["En riesgo de retraso"] if riesgo else AZUL),
        ("Avance operativo promedio", pct(v["Avance (%)"].mean()), ""),
        ("Avance de la meta promedio", pct(v["Avance de la meta (%)"].mean()), ""),
        ("Actualizadas esta semana", f"{camb} / {len(v)}", f"respecto al {fecha(ant)}" if ant else "sin registro previo",
         AMARILLO if camb < len(v) else AZUL)])

    # ------------------------------------------------------------------ el grafico principal: cada accion contra la meta del 100 %
    _hacia_la_meta(v, sel_tipo in (None, "Todas"))

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
        dona_estado(v, ESTADOS_FEN, "Estado actual")
        g = v.groupby("Dirección").size()
        st.markdown("**Acciones por dirección:** " + " · ".join(f"{k} {int(n)}" for k, n in g.items()))

    # ------------------------------------------------------------------ avance por acción (nombre corto)
    etq = v["N°"].astype(str) + " · " + v["Dirección"] + " · " + v["Nombre corto"].astype(str)
    grafico(barras_avance(v, etq, "% de avance operativo por acción",
                          ["Tipo de meta", "Eje corto", "Meta 2026", "Meta 2027", "Meta ejecutada", "Avance de la meta (%)", "Fecha de reporte"]),
            alto=max(420, 34 * len(v) + 120))
    st.caption("La barra es el avance operativo que cada dirección reporta. El avance de la meta (ejecutada / meta del año) "
               "se ve al pasar el mouse y en la tabla de metas.")

    a, b = st.columns(2)
    with a:
        _por_eje(v)
    with b:
        por_direccion(v, "Avance promedio por dirección")

    evolucion(hist, v, "Clave", D["ahora"], "Evolución del avance")
    seccion_historia(hist, v, "Clave", D["ahora"], "fen")

    # ------------------------------------------------------------------ metas
    st.markdown("### Metas: lo comprometido y lo ejecutado")
    tabla = v[["N°", "Dirección", "Tipo de meta", "Eje corto", "Nombre corto", "Unidad", "Meta 2026", "Meta 2027", "Meta ejecutada",
               "Avance de la meta (%)", "Avance (%)", "Fecha de reporte", "Estado actual"]]
    st.dataframe(tabla, width="stretch", hide_index=True, height=min(560, 40 * len(tabla) + 60),
                 column_config={"Nombre corto": st.column_config.TextColumn("Acción (nombre corto)", width="large"), "Eje corto": "Eje temático",
                                "Avance de la meta (%)": st.column_config.ProgressColumn("Avance de la meta (C/A)", format="%d %%", min_value=0, max_value=100),
                                "Avance (%)": st.column_config.ProgressColumn("Avance operativo", format="%d %%", min_value=0, max_value=100)})

    # ------------------------------------------------------------------ fichas
    st.markdown("### Ficha de cada acción")
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


def _hacia_la_meta(v: pd.DataFrame, por_tipo: bool) -> None:
    """Barras horizontales: cada accion en el eje Y con su nombre corto completo y el avance de 0 a 100 % en el eje X,
    con la meta (100 %) como linea; color = tipo de meta y grupos por tipo. Pedido del 26/10/2026."""
    orden = [t for t in TIPOS_META + ["Sin tipo"] if (v["Tipo de meta"] == t).any()]
    d = v.assign(_t=v["Tipo de meta"].map({t: i for i, t in enumerate(orden)}), _a=v["Avance (%)"].fillna(0))
    d = d.sort_values(["_t", "_a"], ascending=[True, False]).reset_index(drop=True)
    # nombre corto entero (en dos lineas si es largo), con su numero
    def partir(t: str, ancho: int = 46) -> str:
        t = str(t)
        if len(t) <= ancho:
            return t
        corte = t.rfind(" ", 0, ancho)
        corte = corte if corte > 15 else ancho
        resto = t[corte:].strip()
        return t[:corte].strip() + "<br>" + (resto if len(resto) <= ancho else resto[:ancho - 1].rstrip() + "…")
    y = [f"<b>{n}</b> · {partir(c)}" for n, c in zip(d["N°"], d["Nombre corto"])]
    fig = go.Figure()
    # banda de fondo por tipo de meta, con su nombre a la derecha
    ini = 0
    for t in orden:
        n = int((d["Tipo de meta"] == t).sum())
        if n == 0:
            continue
        fig.add_hrect(y0=ini - 0.5, y1=ini + n - 0.5, fillcolor=COLOR_TIPO[t], opacity=0.08, line_width=0)
        fig.add_annotation(x=1.0, xref="paper", xanchor="right", y=ini - 0.5, yanchor="top", text=f"<b>{t}</b> · {n}",
                           showarrow=False, font=dict(size=13, color=COLOR_TIPO[t]), bgcolor="rgba(255,255,255,.85)")
        ini += n
    fig.add_bar(y=y, x=[100] * len(d), orientation="h", marker=dict(color="#EEF1F6", line=dict(width=0)), width=0.62,
                hoverinfo="skip", showlegend=False)
    fig.add_bar(y=y, x=d["_a"], orientation="h", width=0.62,
                marker=dict(color=[COLOR_TIPO.get(t, "#B0BEC5") for t in d["Tipo de meta"]], line=dict(width=0), cornerradius=4),
                text=[f"{a:.0f} %" for a in d["_a"]], textposition="outside", textfont=dict(size=12.5, color="#1B2A4A"), cliponaxis=False,
                customdata=d[["Nombre corto", "Dirección", "Tipo de meta", "Eje corto", "Estado actual", "Meta 2026", "Meta 2027", "Meta ejecutada"]].astype(str).values,
                hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}<br>Eje: %{customdata[3]}<br>"
                              "Estado: %{customdata[4]}<br>Avance: %{x:.0f} %<br>Meta 2026: %{customdata[5]} · Meta 2027: %{customdata[6]} · "
                              "Ejecutada: %{customdata[7]}<extra></extra>", showlegend=False)
    # marca de estado a la derecha de la cifra
    simb = {"Implementado": ("star", COLOR_ESTADO["Implementado"]), "En riesgo de retraso": ("triangle-up", COLOR_ESTADO["En riesgo de retraso"]),
            "Sin iniciar": ("circle-open", "#90A4AE")}
    for est, (s, c) in simb.items():
        m = d["Estado actual"] == est
        if m.any():
            fig.add_scatter(y=[yi for yi, k in zip(y, m) if k], x=[a + 10 for a in d.loc[m, "_a"]], mode="markers", name=est,
                            marker=dict(symbol=s, size=12, color=c, line=dict(width=1.5, color=c)), hoverinfo="skip")
    fig.add_vline(x=100, line=dict(color=AMARILLO, width=2, dash="dash"))
    for t in orden:
        fig.add_bar(y=[None], x=[None], name=t, marker=dict(color=COLOR_TIPO[t]))
    fig = fig_base(fig, alto=max(360, 46 * len(d) + 130))
    fig.update_layout(title="Cuánto falta para la meta: avance de cada acción", barmode="overlay", bargap=0.25,
                      yaxis=dict(autorange="reversed", tickfont=dict(size=12.5), automargin=True, showgrid=False),
                      xaxis=dict(range=[0, 138], tickvals=[0, 25, 50, 75, 100], ticktext=["0 %", "25 %", "50 %", "75 %", "100 %"], gridcolor="#EEF1F6", tickfont=dict(size=12.5)),
                      legend=dict(orientation="h", y=1.0, x=0, yanchor="bottom", font=dict(size=12)),
                      margin=dict(l=10, r=10, t=80, b=30))
    st.plotly_chart(fig, width="stretch")
    st.caption("Cada barra es una acción con su nombre corto; el eje va de 0 a 100 % y la línea amarilla es la meta. El color es el tipo de "
               "meta. ★ implementada · ▲ en riesgo · ○ sin iniciar. Pasa el mouse para ver dirección, eje, estado y metas.")


def _cifras(items: list[tuple]) -> None:
    # cifras en HTML: st.metric cortaba «100 %» en «10…» cuando la tarjeta es angosta
    st.markdown('<div style="display:flex;gap:14px;flex-wrap:wrap;margin:2px 0 8px 0">' + "".join(
        f'<div style="min-width:70px"><div style="font-size:.8rem;color:{GRIS_TXT}">{t}</div>'
        f'<div style="font-size:1.7rem;font-weight:700;line-height:1.1;white-space:nowrap">{x}</div></div>' for t, x in items)
        + "</div>", unsafe_allow_html=True)


_CSS_MAPA = f"""
<style>
.accs {{display:grid;grid-template-columns:repeat(auto-fill,minmax(235px,1fr));gap:10px;margin:4px 0 16px 0;}}
.acc {{background:#fff;border:1px solid {LINEA};border-radius:10px;padding:10px 12px 9px 12px;border-left:6px solid #B0BEC5;
       box-shadow:0 1px 2px rgba(27,42,74,.06);}}
.acc .top {{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:6px;}}
.acc .num {{font-size:.8rem;color:{GRIS_TXT};font-weight:600;}}
.acc .etq {{font-size:.72rem;padding:2px 9px;margin:0;}}
.acc .nom {{font-size:.95rem;font-weight:600;color:{TINTA};line-height:1.25;min-height:2.5em;margin-bottom:7px;}}
.acc .bar {{height:9px;background:#EEF1F6;border-radius:5px;overflow:hidden;}}
.acc .bar div {{height:9px;border-radius:5px;}}
.acc .pie {{display:flex;justify-content:space-between;font-size:.8rem;color:{GRIS_TXT};margin-top:5px;}}
.acc .pie b {{color:{TINTA};}}
.grp {{display:flex;align-items:baseline;gap:10px;margin:10px 0 2px 0;padding-bottom:4px;border-bottom:2px solid {LINEA};}}
.grp .t {{font-size:1.05rem;font-weight:700;color:{AZUL};}}
.grp .s {{font-size:.85rem;color:{GRIS_TXT};}}
</style>"""

_AGRUPAR = {"Eje temático": "Eje corto", "Estado actual": "Estado actual", "Dirección": "Dirección", "Tipo de meta": "Tipo de meta"}


def _mapa(v: pd.DataFrame) -> None:
    """Tablero de tarjetas: una tarjeta por accion (borde y etiqueta = estado, barra = avance operativo),
    agrupadas por lo que elija el usuario. Sustituye al mapa de rectangulos, que no se entendia."""
    st.markdown("### Mapa de acciones")
    modo = st.pills("Agrupar las acciones por", list(_AGRUPAR), default="Eje temático", key="mapafen")
    col = _AGRUPAR[modo or "Eje temático"]
    st.markdown(_CSS_MAPA, unsafe_allow_html=True)
    if col == "Estado actual":
        grupos = [e for e in ESTADOS_FEN if (v[col] == e).any()] + [g for g in v[col].dropna().unique() if g not in ESTADOS_FEN]
    else:
        grupos = list(v[col].fillna("Sin dato").value_counts().index)
    html = []
    for g in grupos:
        d = v[v[col].fillna("Sin dato") == g].sort_values("Avance (%)", ascending=False)
        impl = int((d["Estado actual"] == "Implementado").sum())
        color_g = {"Estado actual": COLOR_ESTADO, "Dirección": COLOR_DIR, "Tipo de meta": COLOR_TIPO}.get(col, {}).get(g, AZUL)
        html.append(f'<div class="grp"><span class="t" style="color:{color_g}">{g}</span>'
                    f'<span class="s">{len(d)} acción{"es" if len(d) != 1 else ""} · avance promedio {pct(d["Avance (%)"].mean())}'
                    f' · {impl} implementada{"s" if impl != 1 else ""}</span></div><div class="accs">')
        for _, r in d.iterrows():
            est = r["Estado actual"] or "Sin estado"
            c_est = COLOR_ESTADO.get(est, "#B0BEC5")
            av = 0 if pd.isna(r["Avance (%)"]) else max(0, min(100, float(r["Avance (%)"])))
            nombre = str(r["Nombre corto"])
            completo = str(r["Actividad"]).replace('"', "'")
            extra = etiqueta("Actualizada", AMARILLO) if r["Cambió"] else ""
            html.append(
                f'<div class="acc" style="border-left-color:{c_est}" title="{completo}">'
                f'<div class="top"><span class="num">N° {r["N°"]}</span>{etiqueta(r["Dirección"], COLOR_DIR.get(r["Dirección"], AZUL))}'
                f'{etiqueta(est, c_est)}{extra}</div>'
                f'<div class="nom">{nombre}</div>'
                f'<div class="bar"><div style="width:{av:.0f}%;background:{c_est}"></div></div>'
                f'<div class="pie"><span>Avance <b>{pct(r["Avance (%)"])}</b></span><span>Meta <b>{pct(r["Avance de la meta (%)"])}</b></span>'
                f'<span>{r["Eje corto"] if col != "Eje corto" else r["Tipo de meta"]}</span></div></div>')
        html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)
    st.caption("Cada tarjeta es una acción: el color del borde y la etiqueta son el estado que declara la dirección; la barra es el "
               "avance operativo; «Meta» es lo ejecutado sobre la meta del año. Pasa el mouse por una tarjeta para ver el nombre "
               "completo; la ficha detallada está más abajo.")


def _por_eje(v: pd.DataFrame) -> None:
    d = (v.groupby("Eje corto").agg(Acciones=("Avance (%)", "size"), Avance=("Avance (%)", "mean"),
                                   Impl=("Estado actual", lambda s: int((s == "Implementado").sum()))).reset_index().sort_values("Avance"))
    fig = go.Figure(go.Bar(x=d["Avance"].fillna(0), y=d["Eje corto"], orientation="h", marker=dict(color=AZUL),
                           text=[f"{pct(a)}  ·  {int(n)} acc.  ·  {int(i)} impl." for a, n, i in zip(d["Avance"], d["Acciones"], d["Impl"])],
                           textposition="outside", textfont=dict(size=12), hovertemplate="%{y}: %{x:.0f} % promedio<extra></extra>"))
    fig.update_layout(title="Avance promedio por eje temático", xaxis=dict(range=[0, 175], visible=False), yaxis=dict(tickfont=dict(size=12.5)))
    grafico(fig, alto=max(300, 38 * len(d) + 110), leyenda=False)
