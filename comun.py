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
.kpi {{background:#fff;border-radius:12px;padding:16px 20px;border:1px solid {LINEA};border-left:6px solid {AZUL};min-height:108px;}}
.kpi .l {{font-size:.9rem;color:{GRIS_TXT};}}
.kpi .v {{font-size:2.3rem;font-weight:700;color:{AZUL};line-height:1.15;}}
.kpi .s {{font-size:.9rem;color:{GRIS_TXT};}}
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


def kpi(col, etiqueta, valor, sub="", color=AZUL) -> None:
    col.markdown(f'<div class="kpi" style="border-left-color:{color}"><div class="l">{etiqueta}</div>'
                 f'<div class="v" style="color:{color}">{valor}</div><div class="s">{sub}</div></div>',
                 unsafe_allow_html=True)


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
    etq = etq.iloc[::-1]
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
    fig.update_layout(barmode="overlay", xaxis=dict(range=[0, 112], ticksuffix=" %", showgrid=False),
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


def evolucion(hist: pd.DataFrame, actual: pd.DataFrame, clave: str, hoy, titulo: str) -> None:
    """Curva semana a semana: instantaneas del historial + la lectura de hoy."""
    import plotly.graph_objects as go
    h = hist[hist[clave].isin(actual[clave]) & hist["Avance (%)"].notna()].copy()
    vivo = actual[[clave, "Avance (%)"]].dropna().assign(Fecha=pd.Timestamp(hoy))
    h = pd.concat([h[h["Fecha"].dt.date < hoy], vivo], ignore_index=True).sort_values("Fecha")
    if h.empty:
        st.info("Aún no hay instantáneas semanales para dibujar la evolución.")
        return
    nombres = actual.set_index(clave)["Nombre corto"]
    dirs = actual.set_index(clave)["Dirección"]
    fig = go.Figure()
    for k, gg in h.groupby(clave):
        nom = f"{k}".replace("SENAMHI-", "")
        fig.add_scatter(x=gg["Fecha"], y=gg["Avance (%)"], mode="lines+markers", name=nom,
                        line=dict(width=2, color=COLOR_DIR.get(dirs.get(k), "#999")), marker=dict(size=8),
                        hovertemplate=f"<b>{nombres.get(k, k)}</b><br>%{{x|%d/%m/%Y}}: %{{y:.0f}} %<extra></extra>")
    fig.add_vline(x=pd.Timestamp(hoy), line=dict(color=AMARILLO, width=2, dash="dash"))
    fig.update_layout(title=titulo, yaxis=dict(range=[0, 108], ticksuffix=" %", gridcolor="#EEF1F6"),
                      xaxis=dict(tickformat="%d/%m", gridcolor="#EEF1F6"))
    grafico(fig, alto=400)


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
