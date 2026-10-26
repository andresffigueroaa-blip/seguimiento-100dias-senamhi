# -*- coding: utf-8 -*-
"""Revisa las dos matrices de Drive y guarda en datos/historial_*.csv cada cambio.

    python snapshot.py

Se corre cada hora en dias habiles (GitHub Actions, registro_cambios.yml).
Solo agrega filas para las actividades cuyo avance, estado o detalle cambio
desde su ultimo registro; si nada cambio, no toca los archivos.
"""
from __future__ import annotations

import datos


def main() -> None:
    D = datos.cargar()
    for aviso in D["avisos"]:
        print("aviso:", aviso)
    if D["fuentefen"] != "drive":
        raise SystemExit("No se leyó Drive: no se registra nada para no mezclar la copia local con el historial.")
    ahora = datos.ahora_local()
    c2 = datos.registrar_cambios(datos.HIST_FEN, D["fen"], "Clave", ahora)
    print(f"{ahora:%d/%m/%Y %H:%M}: matriz de acciones prioritarias {len(c2)} cambios {c2}")


if __name__ == "__main__":
    main()
