# Dashboard · Seguimiento Prioridades 100 días · SENAMHI

App independiente (Streamlit) que muestra el avance semanal de las 13
actividades comprometidas por SENAMHI en la Matriz de Prioridades de los
primeros 100 días (Sector Ambiente). Lee el Google Sheet que llenan las
direcciones y se publica como app **privada** en Streamlit Community Cloud.

```
apps/seguimiento100/
  app.py            la página
  datos.py          lectura del Sheet (CSV publicado) y respaldo local
  datos/            copia del libro de seguimiento (respaldo)
  assets/           logos
  .streamlit/       tema y ejemplo de secrets
  requirements.txt
```

## Probar en la PC

```
cd apps/seguimiento100
python -m streamlit run app.py
```
Sin `secrets.toml` usa el libro de `datos/` y avisa que es una copia local.

## Publicar (una sola vez, unos 30 minutos)

### 1. El Google Sheet
1. Subir `deliverables/seguimiento100/Seguimiento_100dias_SENAMHI.xlsx` a
   Drive → clic derecho → *Abrir con → Hojas de cálculo de Google* →
   *Archivo → Guardar como hoja de cálculo de Google*.
2. *Archivo → Compartir → Publicar en la web* → pestaña **Calculos**,
   formato **Valores separados por comas (.csv)** → *Publicar* → copiar el
   enlace. Repetir para **Historial** y **Hitos_RutaElNino**.
3. *Compartir* (botón azul): dar **Editor** a los enlaces de las
   direcciones y a la coordinación (SVC). Copiar el enlace normal del Sheet.

### 2. El repositorio en GitHub
1. Crear cuenta en github.com (o usar la existente).
2. *New repository* → nombre `seguimiento-100dias-senamhi` → **Private**.
3. Subir el contenido de esta carpeta (`apps/seguimiento100`) al repositorio:
   `app.py`, `datos.py`, `requirements.txt`, `assets/`, `datos/`,
   `.streamlit/config.toml`, `.gitignore`. **No subir** `secrets.toml`.
   Desde la carpeta: `git init && git add . && git commit -m "app" &&
   git branch -M main && git remote add origin <url> && git push -u origin main`.

### 3. Streamlit Community Cloud
1. Entrar a share.streamlit.io con la cuenta de GitHub.
2. *Create app → Deploy a public app from GitHub* → elegir el repositorio,
   rama `main`, archivo `app.py`. Nombre de la app: `seguimiento100-senamhi`.
3. *Advanced settings → Secrets*: pegar el contenido de
   `.streamlit/secrets.toml.example` con los tres enlaces CSV, el enlace del
   Sheet y una `PASSWORD`.
4. *Deploy*. En 2 o 3 minutos queda en `https://seguimiento100-senamhi.streamlit.app`.
5. **Hacerla privada**: en la app, *Settings → Sharing* → desmarcar "Public"
   y agregar en *Viewers* los correos @senamhi.gob.pe que podrán entrar
   (entran con su cuenta de Google). Solo esos correos verán la app, y
   además pedirá la clave.

### 4. Actualizar después
- **Datos**: nada que hacer; la app lee el Sheet cada 5 minutos (botón
  *Actualizar datos* para forzar).
- **La app**: cambiar el código en el repositorio y hacer `git push`;
  Streamlit Cloud la vuelve a publicar sola.
- **El libro**: si se regenera con `python -m etl.seguimiento100.build_sheet`,
  copiar el nuevo `.xlsx` a `datos/` (respaldo) y, si cambió la
  estructura, volver a publicar las pestañas CSV.

## Privacidad

Dos capas: la app es privada por correo (Streamlit) y pide clave
(`PASSWORD`). Los CSV publicados del Sheet son accesibles para quien tenga
su enlace largo; contienen la matriz del MINAM y los avances, sin datos
personales. Si se quiere cerrar también eso, se cambia la lectura a la API
de Google Sheets con una cuenta de servicio (requiere crear credenciales en
Google Cloud; se deja para una segunda fase).
