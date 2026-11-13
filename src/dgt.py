"""Descarga las incidencias de tráfico de la DGT (DATEX II) y filtra por provincia.

Uso:
    python dgt.py --keys              # imprime el XML crudo del primer registro
    python dgt.py                     # crea dgt.json con las incidencias de Valencia
    python dgt.py --provincia alicante   # otra provincia (sin tildes, da igual mayúsculas)
"""
import json
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter

import requests

URL = "https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v37.xml"
XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"

# Cómo se dice cada tipo en una frase de excusa
FRASES = {
    "accidente": "un accidente",
    "vehiculo_parado": "un vehículo averiado o parado",
    "obstaculo": "un obstáculo en la calzada",
    "meteo": "condiciones meteorológicas adversas",
    "infraestructura": "daños en la infraestructura",
    "obras": "obras",
    "corte": "un corte de carril",
    "retencion": "una retención",
    "otro": "una incidencia",
}


# ---------- utilidades XML ----------
# El XML usa prefijos de namespace (ns0:, ns3:...). Para no depender de ellos
# comparamos solo el "nombre local": '{http://...}roadName' -> 'roadName'.

def local(tag):
    return tag.rsplit("}", 1)[-1]


def primero(elem, nombre):
    """Texto del primer descendiente con ese nombre local (o None)."""
    for e in elem.iter():
        if local(e.tag) == nombre and e.text and e.text.strip():
            return e.text.strip()
    return None


def primero_dentro(elem, padre):
    """Primer texto que haya dentro del elemento 'padre' (sea cual sea su etiqueta)."""
    for e in elem.iter():
        if local(e.tag) == padre:
            for h in e.iter():
                if h is not e and h.text and h.text.strip():
                    return h.text.strip()
    return None


def sin_tildes(texto):
    """'València/Valencia' -> 'valencia/valencia' para comparar sin líos de acentos."""
    n = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in n if unicodedata.category(c) != "Mn").lower()


# ---------- descarga y extracción ----------

def descargar(url=URL):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return ET.fromstring(r.content)


def registros(raiz):
    """Todos los <situationRecord> del documento."""
    return [e for e in raiz.iter() if local(e.tag) == "situationRecord"]


def extraer(rec):
    """Campos útiles de un registro, tal cual vienen (sin interpretar)."""
    tipo_xsi = rec.attrib.get(XSI_TYPE, "")
    return {
        "tipo_xsi": tipo_xsi.split(":")[-1],
        "causa": primero(rec, "causeType"),
        "detalle": primero_dentro(rec, "detailedCauseType"),  # p. ej. roadworks
        "gravedad": primero(rec, "overallSeverity") or primero(rec, "severity"),
        "via": primero(rec, "roadName"),
        "km": primero(rec, "kilometerPoint"),
        "municipio": primero(rec, "municipality"),
        "provincia": primero(rec, "province"),
        "ccaa": primero(rec, "autonomousCommunity"),
        "inicio": primero(rec, "overallStartTime"),
        "fin": primero(rec, "overallEndTime"),
        "estado": primero(rec, "validityStatus"),
    }


# ---------- estructura común del proyecto ----------

def clasificar(d):
    """Tipo de excusa que se puede construir con esta incidencia.

    EL ORDEN IMPORTA: 'vehicleObstruction' y 'infrastructureDamageObstruction'
    contienen la palabra 'obstruction', así que van antes que 'obstruction' a secas.
    """
    t = sin_tildes(" ".join(filter(None, [d["tipo_xsi"], d["causa"], d["detalle"]])))
    reglas = [
        ("accident", "accidente"),
        ("vehicle", "vehiculo_parado"),
        ("poorenvironment", "meteo"),
        ("infrastructure", "infraestructura"),
        ("obstruction", "obstaculo"),
        ("maintenance", "obras"),
        ("roadworks", "obras"),
        ("construction", "obras"),
        ("lane", "corte"),
        ("carriageway", "corte"),
        ("traffic", "retencion"),
        ("congestion", "retencion"),
        ("queue", "retencion"),
    ]
    for clave, tipo in reglas:
        if clave in t:
            return tipo
    return "otro"


def normalizar(d):
    tipo = clasificar(d)
    sitio = d["via"] or "la carretera"
    if d["km"]:
        sitio += f" km {d['km']}"
    if d["municipio"]:
        sitio += f" ({d['municipio']})"
    return {
        "fuente": "dgt",
        "tipo": tipo,
        "zona": d["municipio"] or d["provincia"],
        "descripcion": f"{FRASES[tipo]} en {sitio}",
        "timestamp": d["inicio"],
        "fin": d["fin"],  # fecha de fin prevista (puede ser None)
    }


def main():
    provincia = "valencia"
    if "--provincia" in sys.argv:
        provincia = sin_tildes(sys.argv[sys.argv.index("--provincia") + 1])

    raiz = descargar()
    todos = registros(raiz)
    if not todos:
        sys.exit("No se ha encontrado ningún <situationRecord>. ¿Cambió el formato?")

    datos = [(r, extraer(r)) for r in todos]
    aqui = [(r, d) for r, d in datos if provincia in sin_tildes(d["provincia"])]
    print(f"{len(todos)} registros en total, {len(aqui)} en '{provincia}'")

    if not aqui:
        cuentas = Counter(d["provincia"] for _, d in datos)
        print("Provincias que aparecen:", dict(cuentas.most_common(15)))
        sys.exit("Nada que guardar. Mira cómo se escribe tu provincia en la lista de arriba.")

    if "--keys" in sys.argv:
        print(ET.tostring(aqui[0][0], encoding="unicode"))
        print("\nLo que extraigo de él:")
        print(json.dumps(aqui[0][1], indent=2, ensure_ascii=False))
        return

    salida = [normalizar(d) for _, d in aqui]
    print("Por tipo:", dict(Counter(e["tipo"] for e in salida)))
    with open("dgt.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)
    print(f"{len(salida)} incidencias guardadas en dgt.json")


if __name__ == "__main__":
    main()
