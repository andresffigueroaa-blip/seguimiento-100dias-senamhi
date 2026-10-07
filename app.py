# -*- coding: utf-8 -*-
"""Seguimiento Prioridades 100 dias - SENAMHI.

Dashboard de seguimiento semanal de las 13 actividades comprometidas por
SENAMHI en la Matriz de Prioridades de los primeros 100 dias (Sector
Ambiente, MINAM). Lee el Google Sheet que llenan las direcciones.

    streamlit run app.py
"""
from __future__ import annotations

import base64
import hmac
import io
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from datos import DIA_100, ESTADOS, INICIO_GOBIERNO, NOMBRE_DIR, SITUACIONES, cargar, secreto

AZUL, AMARILLO = "#344E80", "#EFC030"
AZUL_OSCURO, TINTA, GRIS_TXT, LINEA = "#1F3560", "#1B2A4A", "#5B6B8A", "#E3E8F0"
COLOR_ESTADO = {"Sin iniciar": "#B0BEC5", "En proceso": "#1E88E5", "Con riesgo / retraso": "#F9A825",
                "Completado": "#2E7D32", "Reprogramado": "#7A5195"}
COLOR_SIT = {"Completada": "#2E7D32", "En plazo": "#43A047", "Por iniciar": "#90A4AE",
             "Fecha límite vencida": "#C62828", "Sin fecha límite": "#B0BEC5"}
COLOR_DIR = {"DMCA": AZUL, "DHI": "#2A9D8F", "DSCA": "#E07A1F", "DRD": "#7A5195"}

st.set_page_config(page_title="Seguimiento 100 días · SENAMHI", page_icon="assets/logo_senamhi.png",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown(f"""
<style>
.block-container {{padding-top: 2.2rem; padding-bottom: 2rem; max-width: 1500px;}}
html, body, [class*="css"] {{font-size: 16px;}}
.kpi {{background:#fff;border-radius:12px;padding:16px 20px;border:1px solid {LINEA};border-left:6px solid {AZUL};}}
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
</style>""", unsafe_allow_html=True)

LOGO = base64.b64encode(open("assets/logo_senamhi.png", "rb").read()).decode()
LOGO_MINAM = base64.b64encode(open("assets/logo_minam.png", "rb").read()).decode()


# ------------------------------------------------------------------ acceso
def acceso() -> None:
    clave = secreto("PASSWORD")
    if not clave or st.session_state.get("_ok"):
        return
    _, c, _ = st.columns([1, 1.1, 1])
    with c:
        st.markdown(f'<div class="logo-caja" style="text-align:center"><img src="data:image/png;base64,{LOGO}" width="260"></div>',
                    unsafe_allow_html=True)
        st.markdown("#### Seguimiento Prioridades 100 días")
        with st.form("ingreso"):
            p = st.text_input("Clave de acceso", type="password")
            if st.form_submit_button("Entrar", type="primary"):
                if hmac.compare_digest(p.encode(), clave.encode()):
                    st.session_state["_ok"] = True
                    st.rerun()
                st.error("Clave incorrecta.")
    st.stop()


acceso()


# ------------------------------------------------------------------- datos
@st.cache_data(ttl=300, show_spinner="Leyendo el seguimiento…")
def datos():
    return cargar()


calc, hist, hitos, fuente, aviso = datos()
hoy = date.today()
dia = int(calc["Día de gestión"].max()) if len(calc) else (hoy - INICIO_GOBIERNO).days + 1
faltan = (DIA_100 - hoy).days


def pct(x) -> str:
    return "—" if x is None or pd.isna(x) else f"{x:.0f} %"


def fecha(x) -> str:
    return "—" if x is None or pd.isna(x) else f"{x:%d/%m/%Y}"


def kpi(col, etiqueta, valor, sub="", color=AZUL):
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


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown(f'<div class="logo-caja"><img src="data:image/png;base64,{LOGO}" width="100%"></div>',
                unsafe_allow_html=True)
    st.markdown("### Filtros")
    f_est = st.multiselect("Estado actual", ESTADOS, placeholder="Todos")
    f_pri = st.multiselect("Prioridad (MINAM)", ["Alta", "Media", "Baja"], placeholder="Todas")
    f_nino = st.toggle("Solo relacionadas con El Niño")
    st.divider()
    sheet = secreto("SEG100_SHEET_URL")
    if sheet:
        st.link_button("Abrir la hoja de llenado", sheet, icon=":material/edit:", width="stretch")
    if st.button("Actualizar datos", icon=":material/refresh:", width="stretch"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Fuente: Google Sheet, se actualiza cada 5 minutos" if fuente == "sheet"
               else "Fuente: copia local del libro de seguimiento")
    st.caption(f"Gobierno desde el {INICIO_GOBIERNO:%d/%m/%Y}. Día 100: {DIA_100:%d/%m/%Y}. "
               "Las direcciones registran su avance hasta el jueves 17:00; el corte es el viernes.")

# ---------------------------------------------------------------- cabecera
c1, c2, c3 = st.columns([1.1, 4.2, 1.4])
with c1:
    st.markdown(f'<img src="data:image/png;base64,{LOGO}" width="100%" style="max-width:200px">', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="titulo"><h1>Prioridades de los primeros 100 días · Seguimiento semanal</h1>'
                '<p>Actividades de SENAMHI en la Matriz de Prioridades del Sector Ambiente (MINAM). '
                'Cada dirección registra su avance semanal; el corte es el viernes.</p></div>',
                unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="dia"><div class="n">Día {dia}</div><div class="t">de 100 · '
                f'{"faltan " + str(faltan) + " días" if faltan >= 0 else "plazo cumplido"}</div>'
                f'<div class="barra"><div style="width:{min(max(dia, 0), 100)}%"></div></div></div>',
                unsafe_allow_html=True)
if aviso:
    st.warning(aviso, icon=":material/cloud_off:")

# filtro principal por direccion
dirs = ["Todas"] + sorted(calc["Dirección"].dropna().unique())
cnt = calc["Dirección"].value_counts()
sel_dir = st.pills("Dirección", dirs, default="Todas", label_visibility="collapsed",
                   format_func=lambda d: "Todas las direcciones" if d == "Todas" else f"{d} · {cnt.get(d, 0)}")
v = calc.copy()
if sel_dir and sel_dir != "Todas":
    v = v[v["Dirección"] == sel_dir]
    st.caption(NOMBRE_DIR.get(sel_dir, ""))
if f_est:
    v = v[v["Estado actual"].isin(f_est)]
if f_pri:
    v = v[v["Prioridad (MINAM)"].isin(f_pri)]
if f_nino:
    v = v[v["Relacionada con El Niño"] == "Sí"]
v = v.sort_values(["Dirección", "ID"]).reset_index(drop=True)
if v.empty:
    st.info("No hay actividades con esos filtros.")
    st.stop()

# -------------------------------------------------------------------- KPIs
k = st.columns(6)
kpi(k[0], "Actividades", len(v), f"{int((v['Prioridad (MINAM)'] == 'Alta').sum())} de prioridad alta")
kpi(k[1], "Avance promedio", pct(v["Avance (%)"].mean()), "acumulado al último corte")
kpi(k[2], "Completadas", int((v["Situación de plazo"] == "Completada").sum()), "avance al 100 %", COLOR_ESTADO["Completado"])
kpi(k[3], "En proceso", int((v["Estado actual"] == "En proceso").sum()), "según la dirección", COLOR_ESTADO["En proceso"])
venc = int((v["Situación de plazo"] == "Fecha límite vencida").sum())
kpi(k[4], "Con fecha límite vencida", venc, "y avance menor a 100 %", COLOR_SIT["Fecha límite vencida"] if venc else AZUL)
rep = int((v["Reportó esta semana"] == "Sí").sum())
kpi(k[5], "Reportaron esta semana", f"{rep} / {len(v)}", "cierre: jueves 17:00", AMARILLO if rep < len(v) else AZUL)

st.markdown("")
# ------------------------------------------------- avance por actividad + estado
a, b = st.columns([3, 1.3])
with a:
    vv = v.iloc[::-1]
    etq = vv["ID"].str.replace("SENAMHI-", "") + "  " + vv["Nombre corto"].astype(str)
    fig = go.Figure()
    fig.add_bar(y=etq, x=[100] * len(vv), orientation="h", marker=dict(color="#EEF1F6"), width=0.6,
                hoverinfo="skip", showlegend=False)
    fig.add_bar(y=etq, x=vv["Avance (%)"].fillna(0), orientation="h", width=0.6,
                marker=dict(color=[COLOR_ESTADO.get(s, "#B0BEC5") for s in vv["Estado actual"]]),
                text=[pct(x) for x in vv["Avance (%)"]], textposition="outside", textfont=dict(size=13),
                customdata=vv[["Estado actual", "Fecha límite", "Producto", "Meta", "Unidad"]].astype(str).values,
                hovertemplate="<b>%{y}</b><br>Avance: %{x:.0f} %<br>Estado: %{customdata[0]}"
                              "<br>Fecha límite: %{customdata[1]}<br>Entregable: %{customdata[2]}"
                              "<br>Meta: %{customdata[3]} %{customdata[4]}<extra></extra>", showlegend=False)
    for est, col in COLOR_ESTADO.items():
        if est in set(vv["Estado actual"]):
            fig.add_bar(y=[None], x=[None], name=est, marker=dict(color=col))
    fig.update_layout(barmode="overlay", xaxis=dict(range=[0, 112], ticksuffix=" %", showgrid=False),
                      yaxis=dict(tickfont=dict(size=12.5)), title="% de avance acumulado por actividad (color = estado actual)",
                      legend=dict(orientation="h", y=-0.1))
    st.plotly_chart(fig_base(fig, alto=max(400, 34 * len(v) + 120)), width="stretch")
with b:
    c = v["Estado actual"].value_counts().reindex(ESTADOS).fillna(0)
    c = c[c > 0]
    fig = go.Figure(go.Pie(labels=c.index, values=c.values, hole=0.6, sort=False,
                           marker=dict(colors=[COLOR_ESTADO[s] for s in c.index]),
                           textinfo="value", textfont=dict(color="white", size=15),
                           hovertemplate="%{label}: %{value} actividades<extra></extra>"))
    fig.add_annotation(text=f"<b>{len(v)}</b><br><span style='font-size:12px'>actividades</span>",
                       showarrow=False, font=dict(size=24, color=AZUL))
    fig.update_layout(title="Estado actual (lo declara cada dirección)", legend=dict(orientation="v", x=0, y=-0.02))
    st.plotly_chart(fig_base(fig, alto=330), width="stretch")
    p = v["Prioridad (MINAM)"].value_counts()
    st.markdown("**Prioridad según la matriz MINAM:** " + " · ".join(f"{k} {int(n)}" for k, n in p.items()))
    st.markdown(f"**Relacionadas con El Niño (propuesta):** {int((v['Relacionada con El Niño'] == 'Sí').sum())}")

# ------------------------------------------------------------ plazos (Gantt)
st.markdown("### Plazos: cuándo empieza y cuándo vence cada actividad")
MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"]


def fecha_corta(x) -> str:
    return f"{x.day} {MESES_ES[x.month - 1]}"


g = v.dropna(subset=["Fecha límite"]).copy()
g["ini"] = g["Fecha inicio"].fillna(pd.Timestamp(INICIO_GOBIERNO))
g = g.sort_values(["Fecha límite", "ID"], ascending=[False, False])
MS_DIA = 86_400_000
fig = go.Figure()
for _, r in g.iterrows():
    y = r["ID"].replace("SENAMHI-", "") + "  " + str(r["Nombre corto"])[:52]
    col = COLOR_SIT.get(r["Situación de plazo"], "#B0BEC5")
    dur = max((r["Fecha límite"] - r["ini"]).days, 1)
    fig.add_bar(y=[y], x=[dur * MS_DIA], base=[r["ini"]], orientation="h", width=0.62, showlegend=False,
                marker=dict(color=col, opacity=0.28, line=dict(width=0)),
                hovertemplate=(f"<b>{r['Nombre corto']}</b><br>Inicio: {fecha(r['ini'])}<br>"
                               f"Fecha límite: {fecha(r['Fecha límite'])}<br>Avance: {pct(r['Avance (%)'])}<br>"
                               f"{r['Situación de plazo']}<extra></extra>"))
    av = min(max((r["Avance (%)"] or 0) / 100, 0), 1)
    if av > 0:
        fig.add_bar(y=[y], x=[dur * MS_DIA * av], base=[r["ini"]], orientation="h", width=0.62,
                    marker=dict(color=col, line=dict(width=0)), showlegend=False, hoverinfo="skip")
    fig.add_annotation(x=r["Fecha límite"], y=y, text=f"vence {fecha_corta(r['Fecha límite'])}", showarrow=False,
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
x0 = min(g["ini"].min(), pd.Timestamp(INICIO_GOBIERNO)) - pd.Timedelta(days=5)
x1 = max(g["Fecha límite"].max(), pd.Timestamp(DIA_100)) + pd.Timedelta(days=28)
meses = pd.date_range(x0.replace(day=1), x1, freq="MS")
fig.update_layout(barmode="overlay",
                  xaxis=dict(type="date", range=[x0, x1], tickvals=meses,
                             ticktext=[f"1 {MESES_ES[m.month - 1]}" for m in meses], gridcolor="#E3E8F0",
                             tickfont=dict(size=12)),
                  yaxis=dict(tickfont=dict(size=12.5)),
                  title="La barra clara va del inicio a la fecha límite; la parte sólida es lo avanzado. Ordenadas por fecha límite.",
                  legend=dict(orientation="h", y=-0.12))
st.plotly_chart(fig_base(fig, alto=max(380, 36 * len(g) + 130)), width="stretch")

# ----------------------------------------------------- evolucion y direcciones
a, b = st.columns([3, 2])
with a:
    hv = hist[hist["ID"].isin(v["ID"]) & hist["Avance (%)"].notna()].sort_values("Fecha de corte")
    fig = go.Figure()
    for id_, gg in hv.groupby("ID"):
        r = calc[calc["ID"] == id_].iloc[0]
        fig.add_scatter(x=gg["Fecha de corte"], y=gg["Avance (%)"], mode="lines+markers",
                        name=id_.replace("SENAMHI-", ""), line=dict(width=2, color=COLOR_DIR.get(r["Dirección"], "#999")),
                        marker=dict(size=8), customdata=gg[["Nombre corto", "Acciones"]].fillna("").values,
                        hovertemplate="<b>%{customdata[0]}</b><br>%{x|%d/%m/%Y}: %{y:.0f} %<br>%{customdata[1]}<extra></extra>")
    fig.add_vline(x=pd.Timestamp(hoy), line=dict(color=AMARILLO, width=2, dash="dash"))
    fig.update_layout(title="Avance semana a semana (color = dirección)",
                      yaxis=dict(range=[0, 108], ticksuffix=" %", gridcolor="#EEF1F6"),
                      xaxis=dict(tickformat="%d/%m", gridcolor="#EEF1F6"))
    st.plotly_chart(fig_base(fig, alto=400), width="stretch")
with b:
    d = (calc.groupby("Dirección").agg(Actividades=("ID", "count"), Avance=("Avance (%)", "mean"),
                                       Reportaron=("Reportó esta semana", lambda s: (s == "Sí").sum()),
                                       Completadas=("Situación de plazo", lambda s: (s == "Completada").sum()))
         .reset_index().sort_values("Avance", ascending=True))
    fig = go.Figure(go.Bar(x=d["Avance"], y=d["Dirección"], orientation="h",
                           marker=dict(color=[COLOR_DIR.get(x, AZUL) for x in d["Dirección"]]),
                           text=[f"{pct(a)}  ·  {int(n)} act.  ·  {int(rp)} reportaron" for a, n, rp in
                                 zip(d["Avance"], d["Actividades"], d["Reportaron"])],
                           textposition="outside", textfont=dict(size=12),
                           hovertemplate="%{y}: %{x:.0f} % promedio<extra></extra>"))
    fig.update_layout(title="Avance promedio por dirección", xaxis=dict(range=[0, 160], visible=False),
                      yaxis=dict(tickfont=dict(size=14)))
    st.plotly_chart(fig_base(fig, alto=400, leyenda=False), width="stretch")

# ------------------------------------------------------------- fichas
st.markdown("### Ficha de cada actividad")
st.caption("Todo lo que trae la matriz del MINAM más lo que reporta la dirección cada semana.")
for _, r in v.iterrows():
    est, sit = r["Estado actual"], r["Situación de plazo"]
    with st.expander(f"{r['ID'].replace('SENAMHI-', '')}  ·  {r['Nombre corto']}  ·  {pct(r['Avance (%)'])}"):
        st.markdown(etiqueta(est or "Sin estado", COLOR_ESTADO.get(est, "#B0BEC5")) + etiqueta(sit, COLOR_SIT.get(sit, "#B0BEC5"))
                    + etiqueta(f"Prioridad {r['Prioridad (MINAM)'] or '—'}", AZUL)
                    + (etiqueta("Relacionada con El Niño", "#E07A1F") if r["Relacionada con El Niño"] == "Sí" else ""),
                    unsafe_allow_html=True)
        st.progress(min(int(r["Avance (%)"] or 0), 100), text=f"Avance acumulado: {pct(r['Avance (%)'])}  "
                    f"(en la matriz MINAM: {pct(r['Base (%)'])})")
        c1, c2 = st.columns(2)
        c1.markdown(f"**Actividad (matriz):** {r['Actividad']}  \n**Entregable:** {r['Producto']}  \n"
                    f"**Meta:** {r['Meta']} {r['Unidad']}  \n**Línea base:** {r['Línea base'] or '—'}")
        c2.markdown(f"**Dirección:** {NOMBRE_DIR.get(r['Dirección'], r['Dirección'])}  \n"
                    f"**Fechas:** {fecha(r['Fecha inicio'])} → {fecha(r['Fecha límite'])}"
                    f"{'  (' + str(int(r['Días para el límite'])) + ' días)' if pd.notna(r['Días para el límite']) else ''}  \n"
                    f"**Enlace responsable:** {r['Enlace responsable'] or '— (por definir)'}  \n"
                    f"**Último reporte:** {fecha(r['Último corte']) if pd.notna(r['Último corte']) else 'aún sin reporte semanal'}")
        if r["Acciones"]:
            st.markdown(f"**Qué se hizo:** {r['Acciones']}")
        if r["Alertas"]:
            st.markdown(f"**Alertas / riesgos:** {r['Alertas']}")
        if str(r["Link entregable"]).startswith("http"):
            st.link_button("Abrir entregable", r["Link entregable"], icon=":material/open_in_new:")

# ---------------------------------------------------------------- tablas
t1, t2 = st.tabs(["Tabla de seguimiento", "Sin reporte esta semana"])
with t1:
    tabla = v[["ID", "Dirección", "Nombre corto", "Estado actual", "Avance (%)", "Prioridad (MINAM)",
               "Meta", "Unidad", "Fecha límite", "Situación de plazo", "Último corte", "Acciones", "Alertas",
               "Enlace responsable", "Link entregable"]]
    st.dataframe(
        tabla, width="stretch", hide_index=True, height=min(560, 40 * len(tabla) + 60),
        column_config={
            "Nombre corto": st.column_config.TextColumn("Actividad", width="large"),
            "Avance (%)": st.column_config.ProgressColumn("Avance", format="%d %%", min_value=0, max_value=100),
            "Prioridad (MINAM)": "Prioridad",
            "Fecha límite": st.column_config.DateColumn("Fecha límite", format="DD/MM/YYYY"),
            "Último corte": st.column_config.DateColumn("Último reporte", format="DD/MM/YYYY"),
            "Acciones": st.column_config.TextColumn("Qué se hizo", width="medium"),
            "Link entregable": st.column_config.LinkColumn("Entregable", display_text="abrir")})
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        tabla.to_excel(xw, index=False, sheet_name="Seguimiento")
        hist[hist["ID"].isin(v["ID"])].to_excel(xw, index=False, sheet_name="Historial")
    st.download_button("Descargar en Excel", buf.getvalue(), f"seguimiento_100dias_{hoy:%Y%m%d}.xlsx",
                       icon=":material/download:")
with t2:
    sin = v[(v["Reportó esta semana"] == "No") & (v["Situación de plazo"] != "Completada")]
    if sin.empty:
        st.success("Todas las actividades en curso registraron su avance esta semana.")
    else:
        st.markdown(f"**{len(sin)} actividades sin avance registrado en el corte de esta semana.** "
                    "Recordar a los enlaces antes del jueves a las 17:00.")
        st.dataframe(sin[["Dirección", "ID", "Nombre corto", "Enlace responsable", "Semanas sin reportar", "Último corte"]],
                     width="stretch", hide_index=True,
                     column_config={"Nombre corto": st.column_config.TextColumn("Actividad", width="large"),
                                    "Último corte": st.column_config.DateColumn("Último reporte", format="DD/MM/YYYY")})
st.markdown("---")
f1, f2 = st.columns([5, 1])
f1.caption(f"SENAMHI · Dirección de Meteorología, Clima y Ambiente Atmosférico · Datos al {hoy:%d/%m/%Y}. "
           "Fuente: Matriz de Prioridades 100 días del Sector Ambiente (MINAM) y reportes semanales de las direcciones.")
f2.markdown(f'<img src="data:image/png;base64,{LOGO_MINAM}" width="100%" style="max-width:150px;opacity:.85">',
            unsafe_allow_html=True)
