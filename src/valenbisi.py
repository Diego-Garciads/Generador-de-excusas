"""Descarga la disponibilidad de Valenbisi y la guarda en JSON con estructura común.

Uso:
    python valenbisi.py URL --keys   # muestra el primer registro tal cual llega
    python valenbisi.py URL          # descarga y crea valenbisi.json

URL = la URL del recurso JSON del dataset "ValenBisi Disponibilidad".
"""
import json
from pathlib import Path
import sys
from datetime import datetime, timezone

import requests

# Carpeta data/ del proyecto, calculada desde este archivo (así da igual desde dónde se ejecute)
DATA = Path(__file__).resolve().parent.parent / "data"

# URL del recurso JSON de "ValenBisi Disponibilidad". Pégala aquí para no tener que
# pasarla cada vez. Si se pasa una URL al ejecutar, se usa esa en su lugar.
URL = " https://geoportal.valencia.es/server/rest/services/OPENDATA/Trafico/MapServer/228/query?where=1=1&outFields=*&f=json"


def descargar(url):
    """Una sola petición: el recurso devuelve todas las estaciones juntas."""
    r = requests.get(url, timeout=20)
    r.raise_for_status()  # lanza error si el código HTTP no es 2xx
    datos = r.json()

    # El JSON puede venir de tres formas habituales; las unificamos en una lista:
    if isinstance(datos, list):          # [ {...}, {...} ]
        return datos
    if "results" in datos:               # API de Opendatasoft
        return datos["results"]
    if "error" in datos:                 # ArcGIS devuelve errores con código 200
        sys.exit(f"Error del servidor: {datos['error']}")
    if "features" in datos:              # GeoJSON ("properties") o ArcGIS JSON ("attributes")
        return [f.get("properties") or f.get("attributes") for f in datos["features"]]
    sys.exit(f"Formato no reconocido. Claves de primer nivel: {list(datos)}")


def normalizar(reg):
    """Reduce cada estación a la estructura común del proyecto."""
    return {
        "fuente": "valenbisi",
        "tipo": "estacion_bicis",
        "zona": reg.get("address"),
        "bicis_libres": reg.get("available"),
        "huecos_libres": reg.get("free"),
        "total": reg.get("total"),
        # En origen "open" es el texto "T" (abierta) o "F" (cerrada)
        "abierta": reg.get("open") == "T",
        "timestamp": parsear_fecha(reg.get("updated_at")),
    }


def parsear_fecha(texto):
    """Convierte 'dd/mm/aaaa HH:MM:SS' a ISO 8601 ('aaaa-mm-ddTHH:MM:SS')."""
    try:
        return datetime.strptime(texto, "%d/%m/%Y %H:%M:%S").isoformat()
    except (TypeError, ValueError):
        return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    url = args[0] if args else URL
    if not url:
        sys.exit("Falta la URL: pégala en la constante URL o pásala al ejecutar.")

    registros = descargar(url)
    if not registros:
        sys.exit("La URL no ha devuelto registros.")

    if "--keys" in sys.argv:
        print(json.dumps(registros[0], indent=2, ensure_ascii=False))
        return

    salida = [normalizar(r) for r in registros]

    # Comprobar si los datos son recientes (formato ISO: se pueden comparar como texto)
    fechas = sorted(e["timestamp"] for e in salida if e["timestamp"])
    if fechas:
        print(f"Más antigua: {fechas[0]}  |  Más reciente: {fechas[-1]}")
        antig = datetime.now() - datetime.fromisoformat(fechas[-1])
        if antig.total_seconds() > 3600:
            print(f"AVISO: el dato más reciente tiene {antig.days} días de antigüedad."
                  " Estos datos NO son en tiempo real.")

    with open(DATA / "valenbisi.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)
    print(f"{len(salida)} estaciones guardadas en data/valenbisi.json")


if __name__ == "__main__":
    main()
