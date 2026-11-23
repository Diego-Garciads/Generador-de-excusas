"""Programa principal: ejecuta todo el proyecto de principio a fin.

    1. Descarga los datos de cada fuente (cada script guarda su JSON en data/)
    2. Homogeneiza todos los datos en data/homogeneizado.json
    3. Genera una excusa con un dato real

Si la descarga de una fuente falla, se sigue adelante con el último JSON que haya
guardado de esa fuente, para que el programa no se pare por un solo error.

Uso:
    python src/main.py                    # todo el proceso
    python src/main.py --sin-descargar    # usa los datos ya guardados (más rápido)
    python src/main.py --tipo trafico     # excusa de un tipo concreto
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

import homogeneizar
import generador

SRC = Path(__file__).resolve().parent

# Scripts de descarga, en el orden en que se ejecutan.
# Para añadir una fuente nueva, basta con añadir aquí su script.
SCRIPTS_DESCARGA = [
    "dgt.py",
    "eventos.py",
    "valenbisi.py",
    "aemet_descarga.py",
]


def descargar_todo():
    """Ejecuta cada script de descarga como si lo lanzáramos desde la terminal."""
    entorno = dict(os.environ, PYTHONIOENCODING="utf-8")  # para que las tildes salgan bien
    for script in SCRIPTS_DESCARGA:
        print(f"  Descargando con {script}...", end=" ", flush=True)
        resultado = subprocess.run(
            [sys.executable, str(SRC / script)],  # sys.executable = el mismo Python que ejecuta esto
            cwd=SRC.parent,                         # desde la carpeta del proyecto
            capture_output=True, text=True, encoding="utf-8", env=entorno,
        )
        if resultado.returncode == 0:
            ultima_linea = resultado.stdout.strip().splitlines()[-1] if resultado.stdout.strip() else "OK"
            print(ultima_linea)
        else:
            lineas = (resultado.stderr or resultado.stdout).strip().splitlines()
            error = lineas[-1][:100] if lineas else "sin detalle"   # solo la última línea, recortada
            print(f"FALLO ({error}) -> se usan los últimos datos guardados")


def main():
    parser = argparse.ArgumentParser(description="Generador de excusas con datos reales de Valencia")
    parser.add_argument("--sin-descargar", action="store_true", help="no descarga, usa los datos guardados")
    parser.add_argument("--tipo", help="trafico, obras, corte_calle, bici o meteo")
    args = parser.parse_args()

    print("1) DESCARGA DE DATOS")
    if args.sin_descargar:
        print("  (omitida: se usan los datos ya guardados en data/)")
    else:
        descargar_todo()

    print("\n2) HOMOGENEIZACIÓN")
    homogeneizar.main()

    print("\n3) EXCUSA")
    datos = generador.cargar_datos()
    excusa, r = generador.generar_excusa(datos, args.tipo)
    if excusa is None:
        print(f"No hay datos de tipo '{args.tipo}' ahora mismo. Prueba con otro tipo.")
        return
    print("\n" + excusa)
    print(f"  (Fuente: {generador.NOMBRE_FUENTE.get(r['fuente'], r['fuente'])} · zona: {r['zona']})")


if __name__ == "__main__":
    main()
