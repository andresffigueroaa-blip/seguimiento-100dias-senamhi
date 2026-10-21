# -*- coding: utf-8 -*-
"""Estilo y ayudas compartidas por las dos pestanas."""
from __future__ import annotations

import base64

import pandas as pd
import streamlit as st

AZUL, AMARILLO = "#344E80", "#EFC030"
AZUL_OSCURO, TINTA, GRIS_TXT, LINEA = "#1F3560", "#1B2A4A", "#5B6B8A", "#E3E8F0"
COLOR_ESTADO = {"Sin iniciar": "#B0BEC5", "En proceso": "#1E88E5", "Con riesgo / retraso": "#F9A825",
                "En riesgo de retraso": "#F9A825", "Completado": "#2E7D32", "Implementado": "#2E7D32",
                "Reprogramado": "#7A5195"}
COLOR_SIT = {"Completada": "#2E7D32", "En plazo": "#43A047", "Por iniciar": "#90A4AE",
             "Fecha límite vencida": "#C62828", "Sin fecha límite": "#B0BEC5"}
COLOR_DIR = {"DMCA": AZUL, "DHI": "#2A9D8F", "DSCA": "#E07A1F", "DRD": "#7A5195"}
MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"]

CSS = f"""
<style>
.block-container {{padding-top: 2.2rem; padding-bottom: 2rem; max-width: 1500px;}}
html, body, [class*="css"] {{font-size: 16px;}}
.kpis {{display:grid;grid-template-columns:repeat(auto-fit,minmax(178px,1fr));gap:14px;margin:4px 0 18px 0;}}
.kpi {{background:#fff;border-radius:12px;padding:14px 18px;border:1px solid {LINEA};border-left:6px solid {AZUL};}}
.kpi .l {{font-size:.9rem;color:{GRIS_TXT};line-height:1.25;word-break:normal;overflow-wrap:normal;hyphens:none;}}
.kpi .v {{font-size:2.2rem;font-weight:700;color:{AZUL};line-height:1.15;white-space:nowrap;}}
.kpi .s {{font-size:.85rem;color:{GRIS_TXT};line-height:1.25;word-break:normal;overflow-wrap:normal;}}
.dia {{background:{AZUL};color:#fff;border-radius:12px;padding:14px 20px;text-align:center;}}
.dia .n {{font-size:2.6rem;font-weight:800;color:{AMARILLO};line-height:1;}}
.dia .t {{font-size:.95rem;margin-top:4px;}}
.barra {{height:10px;background:rgba(255,255,255,.25);border-radius:5px;margin-top:10px;overflow:hidden;}}
.barra div {{height:10px;background:{AMARILLO};}}
.titulo h1 {{margin:0;font-size:1.9rem;color:{AZUL};line-height:1.15;}}
.titulo p {{margin:4px 0 0 0;color:{GRIS_TXT};font-size:1.05rem;}}
.ficha {{background:#fff;border:1px solid {LINEA};border-radius:12px;padding:14px 18px;margin-bottom:8px;}}
.ficha b {{color:{TINTA};}}
.etq {{display:inline-block;padding:3px 12px;border-radius:999px;color:#fff;font-weight:600;font-size:.85rem;margin-right:6px;}}
.logo-caja {{background:#fff;border:1px solid {LINEA};border-radius:10px;padding:10px 12px;margin-bottom:8px;}}
h3 {{color:{AZUL} !important; font-size:1.35rem !important;}}
.stTabs [data-baseweb="tab"] p {{font-size:1.1rem; font-weight:600;}}
</style>"""


def b64(ruta: str) -> str:
    return base64.b64encode(open(ruta, "rb").read()).decode()


def pct(x) -> str:
    return "—" if x is None or pd.isna(x) else f"{x:.0f} %"


def fecha(x) -> str:
    if x is None or (not isinstance(x, str) and pd.isna(x)):
        return "—"
    return f"{pd.Timestamp(x):%d/%m/%Y}"


def fecha_corta(x) -> str:
    x = pd.Timestamp(x)
    return f"{x.day} {MESES_ES[x.month - 1]}"


def tarjetas(items: list[tuple]) -> None:
    """Fila de tarjetas KPI que se acomoda sola al ancho (no parte las palabras).
    items: (etiqueta, valor, subtitulo[, color])."""
    html = []
    for it in items:
        etq, val, sub = it[:3]
        color = it[3] if len(it) > 3 and it[3] else AZUL
        html.append(f'<div class="kpi" style="border-left-color:{color}"><div class="l">{etq}</div>'
                    f'<div class="v" style="color:{color}">{val}</div><div class="s">{sub}</div></div>')
    st.markdown(f'<div class="kpis">{"".join(html)}</div>', unsafe_allow_html=True)


def etiqueta(texto: str, color: str) -> str:
    return f'<span class="etq" style="background:{color}">{texto}</span>'


def fig_base(fig, alto=380, leyenda=True):
    fig.update_layout(template="plotly_white", height=alto, font=dict(family="Segoe UI, Arial", size=13, color=TINTA),
                      margin=dict(l=10, r=10, t=50, b=10), title_font=dict(size=17, color=AZUL),
                      legend=dict(orientation="h", y=-0.16, title=None, font=dict(size=12)) if leyenda else None,
                      showlegend=leyenda, paper_bgcolor="white", plot_bgcolor="white")
    return fig


def grafico(fig, alto=380, leyenda=True) -> None:
    st.plotly_chart(fig_base(fig, alto, leyenda), width="stretch")


def barras_avance(v: pd.DataFrame, etq: pd.Series, titulo: str, hover_cols: list[str]):
    """Barras horizontales de avance (fondo gris claro + barra del color del estado)."""
    import plotly.graph_objects as go
    vv = v.iloc[::-1]
    # nombres largos apretaban el gráfico y cortaban las cifras: se acortan (el nombre completo va en el hover)
    etq = etq.iloc[::-1].astype(str).map(lambda t: t if len(t) <= 70 else t[:68].rstrip() + "…")
    fig = go.Figure()
    fig.add_bar(y=etq, x=[100] * len(vv), orientation="h", marker=dict(color="#EEF1F6"), width=0.6,
                hoverinfo="skip", showlegend=False)
    fig.add_bar(y=etq, x=vv["Avance (%)"].fillna(0), orientation="h", width=0.6,
                marker=dict(color=[COLOR_ESTADO.get(s, "#B0BEC5") for s in vv["Estado actual"]]),
                text=[pct(x) for x in vv["Avance (%)"]], textposition="outside", textfont=dict(size=13),
                customdata=vv[hover_cols].astype(str).values,
                hovertemplate="<b>%{y}</b><br>Avance: %{x:.0f} %<br>" + "<br>".join(
                    f"{c}: %{{customdata[{i}]}}" for i, c in enumerate(hover_cols)) + "<extra></extra>",
                showlegend=False)
    for est, col in COLOR_ESTADO.items():
        if est in set(vv["Estado actual"]):
            fig.add_bar(y=[None], x=[None], name=est, marker=dict(color=col))
    fig.update_layout(barmode="overlay", xaxis=dict(range=[0, 118], ticksuffix=" %", showgrid=False),
                      yaxis=dict(tickfont=dict(size=12.5)), title=titulo, legend=dict(orientation="h", y=-0.1))
    return fig


def dona_estado(v: pd.DataFrame, orden: list[str], titulo: str, alto=330) -> None:
    import plotly.graph_objects as go
    c = v["Estado actual"].value_counts().reindex(orden).fillna(0)
    c = c[c > 0]
    fig = go.Figure(go.Pie(labels=c.index, values=c.values, hole=0.6, sort=False,
                           marker=dict(colors=[COLOR_ESTADO.get(s, "#B0BEC5") for s in c.index]),
                           textinfo="value", textfont=dict(color="white", size=15),
                           hovertemplate="%{label}: %{value}<extra></extra>"))
    fig.add_annotation(text=f"<b>{len(v)}</b><br><span style='font-size:12px'>actividades</span>",
                       showarrow=False, font=dict(size=24, color=AZUL))
    fig.update_layout(title=titulo, legend=dict(orientation="v", x=0, y=-0.02))
    grafico(fig, alto=alto)


def _serie(hist: pd.DataFrame, actual: pd.DataFrame, clave: str, ahora) -> pd.DataFrame:
    """Historial de cambios + el valor de este momento (para que la linea llegue a hoy)."""
    h = hist[hist[clave].isin(actual[clave])][["Fecha", clave, "Avance (%)", "Estado actual"]].copy()
    vivo = actual[[clave, "Avance (%)", "Estado actual"]].assign(Fecha=pd.Timestamp(ahora))
    return pd.concat([h, vivo], ignore_index=True).sort_values(["Fecha", clave])


def evolucion(hist: pd.DataFrame, actual: pd.DataFrame, clave: str, ahora, titulo: str) -> None:
    """Escalera de avance: cada escalon es una actualizacion registrada en la matriz."""
    import plotly.graph_objects as go
    h = _serie(hist, actual, clave, ahora).dropna(subset=["Avance (%)"])
    if hist.empty or h.empty:
        st.info("El registro empieza hoy: la curva se irá dibujando con cada actualización de la matriz.")
        return
    act = actual.drop_duplicates(clave).set_index(clave)
    nombres, dirs = act["Nombre corto"], act["Dirección"]
    etq = act["Etiqueta"] if "Etiqueta" in act.columns else pd.Series(act.index, index=act.index)
    fig = go.Figure()
    for k, gg in h.groupby(clave):
        nom = str(etq.get(k, k))
        fig.add_scatter(x=gg["Fecha"], y=gg["Avance (%)"], mode="lines+markers", name=nom, line_shape="hv",
                        line=dict(width=2, color=COLOR_DIR.get(dirs.get(k), "#999")), marker=dict(size=7),
                        hovertemplate=f"<b>{nombres.get(k, k)}</b><br>%{{x|%d/%m/%Y %H:%M}}: %{{y:.0f}} %<extra></extra>")
    lunes = pd.date_range(h["Fecha"].min().normalize() - pd.Timedelta(days=h["Fecha"].min().weekday()),
                          pd.Timestamp(ahora) + pd.Timedelta(days=7), freq="W-MON")
    for l in lunes:
        fig.add_vline(x=l, line=dict(color="#C9D1DA", width=1, dash="dot"))
    fig.add_vline(x=pd.Timestamp(ahora), line=dict(color=AMARILLO, width=2, dash="dash"))
    x0 = min(h["Fecha"].min(), pd.Timestamp(ahora) - pd.Timedelta(days=6))
    fig.update_layout(title=titulo, yaxis=dict(range=[0, 108], ticksuffix=" %", gridcolor="#EEF1F6"),
                      xaxis=dict(tickformat="%d/%m", gridcolor="#EEF1F6", range=[x0 - pd.Timedelta(hours=12),
                                                                               pd.Timestamp(ahora) + pd.Timedelta(days=1)]))
    grafico(fig, alto=400)
    st.caption("Cada escalón es una actualización guardada de la matriz en Drive (se revisa cada hora en días hábiles). "
               "Las líneas punteadas marcan el inicio de cada semana.")


def tabla_semanal(hist: pd.DataFrame, actual: pd.DataFrame, clave: str, ahora) -> pd.DataFrame:
    """Avance al cierre de cada semana (domingo) desde que empezo el registro; la semana en curso, al dia de hoy."""
    h = _serie(hist, actual, clave, ahora)
    ini = h["Fecha"].min().normalize()
    ini = ini - pd.Timedelta(days=ini.weekday())
    lunes = pd.date_range(ini, pd.Timestamp(ahora), freq="W-MON")
    filas = []
    for k, gg in h.groupby(clave):
        gg = gg.sort_values("Fecha")
        fila = {clave: k}
        for l in lunes:
            corte = min(l + pd.Timedelta(days=7), pd.Timestamp(ahora) + pd.Timedelta(minutes=1))
            prev = gg[gg["Fecha"] < corte]
            fila[f"Sem. {l:%d/%m}"] = prev["Avance (%)"].iloc[-1] if len(prev) else None
        filas.append(fila)
    t = pd.DataFrame(filas)
    act = actual.drop_duplicates(clave).set_index(clave)
    t.insert(1, "Actividad", t[clave].map(act["Nombre corto"]))
    orden = {k: i for i, k in enumerate(actual[clave])}
    t = t.sort_values(clave, key=lambda c: c.map(orden)).reset_index(drop=True)
    if "Etiqueta" in act.columns:
        t[clave] = t[clave].map(act["Etiqueta"])
        t = t.rename(columns={clave: "N°"})
    return t


def registro_cambios(hist: pd.DataFrame, actual: pd.DataFrame, clave: str) -> pd.DataFrame:
    """Una fila por actualizacion: que cambio (avance, estado, detalle) y cuando."""
    h = hist[hist[clave].isin(actual[clave])].sort_values([clave, "Fecha"]).copy()
    filas = []
    for k, gg in h.groupby(clave):
        prev = None
        for _, r in gg.iterrows():
            if prev is None:
                prev = r
                continue
            cambios = []
            if not (pd.isna(r["Avance (%)"]) and pd.isna(prev["Avance (%)"])) and r["Avance (%)"] != prev["Avance (%)"]:
                cambios.append(f"Avance {pct(prev['Avance (%)'])} → {pct(r['Avance (%)'])}")
            if str(r["Estado actual"]) != str(prev["Estado actual"]):
                cambios.append(f"Estado «{prev['Estado actual'] or '—'}» → «{r['Estado actual'] or '—'}»")
            if str(r.get("Detalle", "")) != str(prev.get("Detalle", "")):
                cambios.append("Detalle actualizado")
            filas.append({"Fecha": r["Fecha"], clave: k, "Qué cambió": " · ".join(cambios) or "—",
                          "Avance (%)": r["Avance (%)"], "Detalle": r.get("Detalle", "")})
            prev = r
    t = pd.DataFrame(filas, columns=["Fecha", clave, "Qué cambió", "Avance (%)", "Detalle"])
    if len(t):
        act = actual.drop_duplicates(clave).set_index(clave)
        t.insert(2, "Actividad", t[clave].map(act["Nombre corto"]))
        if "Etiqueta" in act.columns:
            t[clave] = t[clave].map(act["Etiqueta"])
            t = t.rename(columns={clave: "N°"})
    return t.sort_values("Fecha", ascending=False).reset_index(drop=True)


def seccion_historia(hist: pd.DataFrame, actual: pd.DataFrame, clave: str, ahora, key: str) -> None:
    """Avance semana a semana (tabla) y registro de cambios."""
    st.markdown("### Avance semana a semana")
    if hist.empty:
        st.info("El registro empieza con la primera lectura de la matriz.")
        return
    inicio = hist["Fecha"].min()
    st.caption(f"Avance de cada actividad al cierre de cada semana, según la matriz en Drive. "
               f"Registro desde el {inicio:%d/%m/%Y %H:%M}; la última columna es la semana en curso, al día de hoy.")
    t = tabla_semanal(hist, actual, clave, ahora)
    semanas = [c for c in t.columns if c.startswith("Sem.")]
    st.dataframe(t, width="stretch", hide_index=True, height=min(560, 36 * len(t) + 42),
                 column_config={"Actividad": st.column_config.TextColumn(width="large"),
                                **{c: st.column_config.NumberColumn(c, format="%d %%") for c in semanas}})
    st.markdown("### Registro de cambios")
    r = registro_cambios(hist, actual, clave)
    if r.empty:
        st.caption(f"Sin cambios desde la línea de partida del {inicio:%d/%m/%Y}. Cada vez que una dirección actualice "
                   "su fila en Drive aparecerá aquí, con fecha y hora.")
    else:
        st.dataframe(r, width="stretch", hide_index=True, height=min(480, 36 * len(r) + 42), key=f"reg_{key}",
                     column_config={"Fecha": st.column_config.DatetimeColumn("Fecha y hora", format="DD/MM/YYYY HH:mm"),
                                    "Actividad": st.column_config.TextColumn(width="medium"),
                                    "Avance (%)": st.column_config.NumberColumn("Avance", format="%d %%"),
                                    "Detalle": st.column_config.TextColumn("Detalle registrado", width="large")})


def por_direccion(v: pd.DataFrame, titulo: str) -> None:
    import plotly.graph_objects as go
    d = (v.groupby("Dirección").agg(Actividades=("Avance (%)", "size"), Avance=("Avance (%)", "mean"),
                                    Cambiaron=("Cambió", "sum")).reset_index().sort_values("Avance"))
    fig = go.Figure(go.Bar(x=d["Avance"].fillna(0), y=d["Dirección"], orientation="h",
                           marker=dict(color=[COLOR_DIR.get(x, AZUL) for x in d["Dirección"]]),
                           text=[f"{pct(a)}  ·  {int(n)} act.  ·  {int(c)} actualizaron" for a, n, c in
                                 zip(d["Avance"], d["Actividades"], d["Cambiaron"])],
                           textposition="outside", textfont=dict(size=12),
                           hovertemplate="%{y}: %{x:.0f} % promedio<extra></extra>"))
    fig.update_layout(title=titulo, xaxis=dict(range=[0, 165], visible=False), yaxis=dict(tickfont=dict(size=14)))
    grafico(fig, alto=400, leyenda=False)


def excel(hojas: dict[str, pd.DataFrame]) -> bytes:
    import io
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for nombre, df in hojas.items():
            df.to_excel(xw, index=False, sheet_name=nombre[:31])
    return buf.getvalue()
