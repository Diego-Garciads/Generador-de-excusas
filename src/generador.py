"""Generador de excusas (versión sencilla).

Lee data/homogeneizado.json, elige un dato real al azar y lo convierte en una excusa.

Uso:
    python src/generador.py                # excusa de cualquier tipo
    python src/generador.py --tipo trafico # solo de un tipo: trafico, obras, corte_calle, bici, meteo
"""
import argparse
import json
import random
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
HOMOGENEIZADO = DATA / "homogeneizado.json"

# Formas de empezar la excusa: se elige una al azar para que no suenen todas igual
INICIOS = [
    "Perdona el retraso: ",
    "Siento llegar tarde, ",
    "No te vas a creer lo que me ha pasado: ",
    "Lo siento muchísimo, ",
]

# Nombre de cada fuente para decir de dónde sale el dato (la excusa es comprobable)
NOMBRE_FUENTE = {
    "dgt": "DGT",
    "eventos": "Ayuntamiento de Valencia",
    "valenbisi": "Valenbisi",
    "aemet": "AEMET",
}


def cargar_datos(ruta=HOMOGENEIZADO):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def generar_excusa(datos, tipo=None):
    """Devuelve (texto de la excusa, registro usado), o (None, None) si no hay datos."""
    # 1. Si no se pide un tipo, se elige uno al azar entre los que hay.
    #    Así todos los tipos salen igual de a menudo, aunque de uno haya muchos más datos.
    if tipo is None:
        tipos_disponibles = sorted({r["tipo"] for r in datos})
        if not tipos_disponibles:
            return None, None
        tipo = random.choice(tipos_disponibles)

    # 2. Quedarse con los datos de ese tipo y elegir uno al azar
    candidatos = [r for r in datos if r["tipo"] == tipo]
    if not candidatos:
        return None, None
    r = random.choice(candidatos)

    # 3. Montar la frase. Las descripciones de la DGT y del Ayuntamiento empiezan por
    #    un sustantivo ("obras en...", "un accidente en..."), así que les falta un verbo.
    descripcion = r["descripcion"]
    if r["fuente"] in ("dgt", "eventos"):
        descripcion = "había " + descripcion

    excusa = random.choice(INICIOS) + descripcion + "."
    return excusa, r


def main():
    parser = argparse.ArgumentParser(description="Genera una excusa con datos reales de Valencia")
    parser.add_argument("--tipo", help="trafico, obras, corte_calle, bici o meteo")
    args = parser.parse_args()

    datos = cargar_datos()
    excusa, r = generar_excusa(datos, args.tipo)
    if excusa is None:
        print(f"No hay datos de tipo '{args.tipo}' ahora mismo. Prueba con otro tipo.")
        return

    print("\n" + excusa)
    print(f"  (Fuente: {NOMBRE_FUENTE.get(r['fuente'], r['fuente'])} · zona: {r['zona']})")


if __name__ == "__main__":
    main()
