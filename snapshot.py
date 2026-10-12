# -*- coding: utf-8 -*-
"""Guarda la lectura de hoy de las dos matrices en datos/historial_*.csv.

    python snapshot.py            # fecha de hoy (hora de Lima)
    python snapshot.py 09/10/2026 # otra fecha (p. ej. para reconstruir)

Se corre cada lunes (a mano o con el flujo de GitHub Actions del repositorio)
y da la curva semana a semana del dashboard. Lee de Drive si hay enlaces en
secrets/variables de entorno; si no, de las copias de datos/.
"""
from __future__ import annotations

import sys
from datetime import datetime

import datos


def main() -> None:
    fecha = datetime.strptime(sys.argv[1], "%d/%m/%Y").date() if len(sys.argv) > 1 else datos.ahora_lima().date()
    D = datos.cargar()
    for aviso in D["avisos"]:
        print("aviso:", aviso)
    n1 = datos.guardar_instantanea(datos.HIST_100, D["m100"], "ID", fecha)
    n2 = datos.guardar_instantanea(datos.HIST_FEN, D["fen"], "N°", fecha)
    print(f"{fecha:%d/%m/%Y}: 100 días {len(D['m100'])} actividades ({n1} filas en historial) · "
          f"FEN {len(D['fen'])} acciones ({n2} filas en historial)")


if __name__ == "__main__":
    main()
