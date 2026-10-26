# Dashboard · Seguimiento de prioridades · SENAMHI

App Streamlit con dos pestañas:

1. **Prioridades 100 días**: las 13 actividades de SENAMHI en la Matriz de
   Prioridades del Sector Ambiente (MINAM).
2. **Acciones prioritarias FEN 2026**: la matriz de acciones en el marco del FEN.

Las dos matrices viven en **Drive** (archivos .xlsx compartidos). Cada dirección
actualiza su fila ahí; la app los descarga cada 5 minutos. No hay otro archivo
intermedio.

```
app.py          clave, cabecera, barra lateral y las dos pestañas
datos.py        lectura de las dos matrices (Drive o copia local) e historial
vista100.py     pestaña Prioridades 100 días
vistafen.py     pestaña FEN
comun.py        estilo (colores SENAMHI) y gráficos compartidos
snapshot.py     guarda la lectura de hoy en datos/historial_*.csv (curva semanal)
datos/          copias locales de las matrices e historial semanal
.github/workflows/instantanea_semanal.yml   corre snapshot.py cada lunes
test_app.py     prueba de humo
```

## Secrets (Streamlit Cloud → Settings → Secrets)

```toml
MATRIZ_100DIAS_URL = "https://drive.google.com/file/d/<id>/view"
MATRIZ_FEN_URL = "https://drive.google.com/file/d/<id>/view"
PASSWORD = "clave"
```
Los archivos deben estar compartidos como «Cualquier persona con el enlace».
Si falta un enlace o falla la descarga, la app usa la copia de `datos/` y lo avisa.

## Evolución semanal

`snapshot.py` guarda el avance y el estado de cada actividad con la fecha del
día. El flujo de GitHub Actions lo corre cada hora de lunes a viernes (07:00-19:00 Lima) y sube el
resultado; requiere los dos enlaces como *secrets* del repositorio
(Settings → Secrets and variables → Actions). También se puede correr a mano:
`python snapshot.py` o `python snapshot.py 09/10/2026`.

## Probar en la PC

```
python -m streamlit run app.py
```

## Una sola matriz y tipo de meta (26/10/2026)

Desde el 26/10/2026 el tablero lee **solo la matriz de acciones prioritarias** (Drive, `MATRIZ_FEN_URL`);
la matriz MINAM de 100 días ya no se usa (`vista100.py` queda sin uso). Cada acción trae un **Tipo de meta**
(`Matriz 100 días`, `Meta 2026`, `Meta 2027`, `Meta 2026 - 2027`) y un **Nombre corto**; si una fila no
tiene tipo, se deduce de las metas (0 en «Meta al cierre de 2026» o «Meta al 2027» = no es de ese año).
Filtros: tipo de meta, dirección, eje temático (nombre corto en `datos.EJES_CORTOS`), agrupación temática
y estado. Los gráficos usan el nombre corto; la ficha de cada acción muestra el nombre completo.
