"""Junta los datos de todas las fuentes en un único formato común.

Cada fuente guarda su JSON en data/ con su propia estructura. Este script los lee,
los traduce todos a la MISMA estructura (el "contrato" del proyecto), los limpia
y filtra, y guarda el resultado en data/homogeneizado.json.

Uso:
    python src/homogeneizar.py

Estructura común de cada registro:
    fuente       str        de dónde viene: "dgt", "eventos", "valenbisi"...
    tipo         str        categoría de excusa: "trafico", "obras", "corte_calle", "bici", "meteo"
    subtipo      str|None   detalle dentro de la categoría (p. ej. "accidente")
    zona         str|None   sitio, en texto
    descripcion  str        frase lista para usar en la excusa
    inicio       str|None   fecha ISO 8601 con zona horaria de Madrid
    fin          str|None   fecha ISO 8601 con zona horaria de Madrid
    detalles     dict       campos propios de cada fuente (no obligatorios)

Para añadir una fuente nueva: escribe una función desde_<fuente>(registros) que
devuelva una lista de registros con la estructura de arriba, y añádela a ADAPTADORES.
"""
import json
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Ruta a data/ calculada desde la ubicación de ESTE archivo, no desde donde se ejecute.
DATA = Path(__file__).resolve().parent.parent / "data"
SALIDA = DATA / "homogeneizado.json"

try:
    MADRID = ZoneInfo("Europe/Madrid")
except ZoneInfoNotFoundError:
    # En Windows no viene la base de datos de zonas horarias: hay que instalarla.
    raise SystemExit("Falta la base de datos de zonas horarias. Ejecuta: pip install tzdata")

CAMPOS = ["fuente", "tipo", "subtipo", "zona", "descripcion", "inicio", "fin", "detalles"]


# ---------- utilidades de limpieza ----------

def fecha_madrid(texto, hora_local=False):
    """Convierte cualquier fecha ISO a ISO con la zona horaria de Madrid.

    - Si la fecha trae zona horaria (+01:00, +00:00...), se convierte a la de Madrid.
    - Si no la trae, o si hora_local=True, se interpreta la hora tal cual como hora
      de Madrid (sirve para fuentes que guardan la hora local marcándola mal como UTC).
    """
    if not texto:
        return None
    try:
        f = datetime.fromisoformat(texto)
    except ValueError:
        return None
    if f.tzinfo is None or hora_local:
        f = f.replace(tzinfo=MADRID)  # mismo reloj, ahora marcado como hora de Madrid
    else:
        f = f.astimezone(MADRID)      # mismo instante, expresado en hora de Madrid
    return f.isoformat(timespec="seconds")


def limpia_zona(texto):
    """Quita espacios sobrantes y, en topónimos bilingües, se queda con uno.

    'Alboraia/Alboraya' -> 'Alboraya'. La DGT pone primero el valenciano y luego
    el castellano; nos quedamos con el último para que todo vaya en el mismo idioma.
    """
    if not texto:
        return None
    texto = " ".join(texto.split())  # colapsa espacios repetidos
    if "/" in texto:
        texto = texto.split("/")[-1].strip()
    return texto or None


def registro(**campos):
    """Crea un registro con TODOS los campos del contrato (los que falten, a None)."""
    r = {c: campos.get(c) for c in CAMPOS}
    r["detalles"] = r["detalles"] or {}
    return r


# ---------- un adaptador por fuente ----------

# Tipos de la DGT -> categoría común de excusa
TIPOS_DGT = {
    "accidente": "trafico",
    "vehiculo_parado": "trafico",
    "obstaculo": "trafico",
    "corte": "trafico",
    "retencion": "trafico",
    "infraestructura": "trafico",
    "otro": "trafico",
    "obras": "obras",
    "meteo": "meteo",
}


# Municipios que consideramos "Valencia y área metropolitana" (comarcas de l'Horta).
# Escritos en minúsculas y sin tildes; si un municipio tiene dos nombres, van los dos.
AREA_METROPOLITANA = {
    "valencia",
    # l'Horta Nord
    "albalat dels sorells", "alboraia", "alboraya", "albuixech", "alfara del patriarca",
    "almassera", "bonrepos i mirambell", "burjassot", "emperador", "foios", "godella",
    "massalfassar", "massamagrell", "meliana", "moncada", "museros", "paterna",
    "la pobla de farnals", "pucol", "el puig de santa maria", "rafelbunyol", "rocafort",
    "tavernes blanques", "vinalesa",
    # l'Horta Oest
    "alaquas", "aldaia", "manises", "mislata", "paiporta", "picanya", "quart de poblet",
    "torrent", "xirivella", "chirivella",
    # l'Horta Sud
    "albal", "alcasser", "alfafar", "beniparrell", "catarroja", "llocnou de la corona",
    "massanassa", "picassent", "sedavi", "silla",
}


def sin_tildes(texto):
    """'València' -> 'valencia', para comparar nombres sin problemas de acentos."""
    n = unicodedata.normalize("NFD", texto)
    return "".join(c for c in n if unicodedata.category(c) != "Mn").lower().strip()


def en_area_metropolitana(zona):
    """True si el municipio está en la lista. Prueba cada nombre de 'Alboraia/Alboraya'."""
    if not zona:
        return False
    return any(sin_tildes(nombre) in AREA_METROPOLITANA for nombre in zona.split("/"))


def desde_dgt(registros):
    salida = []
    for r in registros:
        if not en_area_metropolitana(r.get("zona")):
            continue  # el proyecto es solo de Valencia y su área metropolitana
        salida.append(registro(
            fuente="dgt",
            tipo=TIPOS_DGT.get(r.get("tipo"), "trafico"),
            subtipo=r.get("tipo"),
            zona=limpia_zona(r.get("zona")),
            descripcion=r.get("descripcion"),
            inicio=fecha_madrid(r.get("timestamp")),
            fin=fecha_madrid(r.get("fin")),
        ))
    return salida


def desde_eventos(registros):
    salida = []
    for r in registros:
        salida.append(registro(
            fuente="eventos",
            # 'obras' u 'incidencias' en origen; ambas son cortes de calle
            tipo="obras" if r.get("categoria") == "obras" else "corte_calle",
            subtipo=r.get("categoria"),
            zona=limpia_zona(r.get("zona")),
            descripcion=r.get("descripcion"),
            # El geoportal guarda la hora local (00:00-23:59) marcada como UTC.
            inicio=fecha_madrid(r.get("timestamp"), hora_local=True),
            fin=fecha_madrid(r.get("fin"), hora_local=True),
            detalles={
                "afectacion": r.get("afectacion"),
                "motivo": r.get("motivo"),
                "duracion_dias": r.get("duracion_dias"),
            },
        ))
    return salida


def desde_valenbisi(registros, max_retraso=timedelta(days=1)):
    """Solo interesan las estaciones que dan excusa: vacías, llenas o cerradas.

    Además se descartan las que no se han actualizado en mucho tiempo respecto a la
    más reciente: suelen ser estaciones averiadas con datos congelados.
    """
    fechas = [datetime.fromisoformat(r["timestamp"]) for r in registros if r.get("timestamp")]
    mas_reciente = max(fechas) if fechas else None

    salida = []
    for r in registros:
        if not r.get("timestamp") or mas_reciente is None:
            continue
        if mas_reciente - datetime.fromisoformat(r["timestamp"]) > max_retraso:
            continue  # dato congelado: no es fiable

        zona = limpia_zona(r.get("zona"))
        if not r.get("abierta"):
            subtipo, frase = "cerrada", f"la estación de Valenbisi de {zona} estaba cerrada"
        elif r.get("bicis_libres") == 0:
            subtipo, frase = "sin_bicis", f"no quedaba ninguna bici en la estación de Valenbisi de {zona}"
        elif r.get("huecos_libres") == 0:
            subtipo, frase = "sin_huecos", f"no había hueco para dejar la bici en la estación de Valenbisi de {zona}"
        else:
            continue  # estación normal: no sirve como excusa

        salida.append(registro(
            fuente="valenbisi",
            tipo="bici",
            subtipo=subtipo,
            zona=zona,
            descripcion=frase,
            inicio=fecha_madrid(r["timestamp"]),
            detalles={k: r.get(k) for k in ("bicis_libres", "huecos_libres", "total")},
        ))
    return salida


# A partir de qué valores el tiempo sirve como excusa
LLUVIA_MINIMA_MM = 0.5      # precipitación en la última hora (mm)
RACHA_MINIMA_KMH = 50       # racha máxima de viento (km/h)


def desde_aemet(registros, max_retraso=timedelta(hours=12)):
    """Solo interesa el tiempo ACTUAL de cada estación, y solo si es malo.

    La AEMET da una observación por hora y estación. Nos quedamos con la última
    de cada estación y generamos excusa si llueve o hay rachas fuertes de viento.
    """
    # 1. La observación más reciente de cada estación ('idema' es su código)
    ultima = {}
    for r in registros:
        est = r.get("idema")
        if est and r.get("fint"):
            # Las fechas tienen todas el mismo formato, así que se comparan como texto
            if est not in ultima or r["fint"] > ultima[est]["fint"]:
                ultima[est] = r

    if ultima:     # Filtro de antigüedad: Claude Opus 5.5 (bajo)
        mas_reciente = max(datetime.fromisoformat(r["fint"]) for r in ultima.values())
        ultima = {est: r for est, r in ultima.items()
                  if mas_reciente - datetime.fromisoformat(r["fint"]) <= max_retraso}

    # 2. Excusa solo si el tiempo es malo
    salida = []
    for r in ultima.values():
        # 'SAGUNTO (MONTIVER PONTAZGO...)' -> 'Sagunto'
        zona = (r.get("ubi") or "").split("(")[0].strip().title() or None
        lluvia = r.get("prec") or 0
        racha_kmh = round((r.get("vmax") or 0) * 3.6)  # la AEMET da el viento en m/s

        if lluvia >= LLUVIA_MINIMA_MM:
            subtipo, frase = "lluvia", f"estaba lloviendo con fuerza en {zona} ({lluvia} mm en la última hora)"
        elif racha_kmh >= RACHA_MINIMA_KMH:
            subtipo, frase = "viento", f"había rachas de viento de {racha_kmh} km/h en {zona}"
        else:
            continue  # buen tiempo: no hay excusa

        salida.append(registro(
            fuente="aemet",
            tipo="meteo",
            subtipo=subtipo,
            zona=zona,
            descripcion=frase,
            inicio=fecha_madrid(r["fint"]),
            detalles={"lluvia_mm": lluvia, "racha_kmh": racha_kmh, "temperatura": r.get("ta")},
        ))
    return salida


# Nombre del fichero en data/ (sin .json) -> función que lo traduce.
# Cuando Salva o Edu suban su parte, se añade aquí una línea.
ADAPTADORES = {
    "dgt": desde_dgt,
    "eventos": desde_eventos,
    "valenbisi": desde_valenbisi,
    "aemet": desde_aemet,
}


# ---------- proceso completo ----------

def quitar_duplicados(registros):
    """Dos registros son el mismo si coinciden en todo lo que importa."""
    vistos, unicos = set(), []
    for r in registros:
        clave = (r["fuente"], r["tipo"], r["zona"], r["descripcion"], r["inicio"], r["fin"])
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(r)
    return unicos


def archivo_mas_reciente(fuente):
    """El JSON más reciente de una fuente en data/.

    Sirve tanto para 'dgt.json' como para archivos con la fecha en el nombre,
    como los de AEMET ('aemet_obs_20261122T2230Z.json'). None si no hay ninguno.
    """
    candidatos = list(DATA.glob(f"{fuente}*.json"))
    if not candidatos:
        return None
    return max(candidatos, key=lambda ruta: ruta.stat().st_mtime)  # el modificado más tarde


# Algo que dura más que esto ya no es una novedad: no sirve como excusa
# ("había obras" no cuela si la calle lleva cortada dos años)
DURACION_MAXIMA_DIAS = 60


def duracion_razonable(r):
    """True si el registro no tiene fechas de inicio y fin, o si dura poco."""
    if not r["inicio"] or not r["fin"]:
        return True
    dias = (datetime.fromisoformat(r["fin"]) - datetime.fromisoformat(r["inicio"])).days
    return dias <= DURACION_MAXIMA_DIAS


def homogeneizar():
    todos = []
    for fuente, adaptador in ADAPTADORES.items():
        ruta = archivo_mas_reciente(fuente)
        if ruta is None:
            print(f"[aviso] No hay ningún {fuente}*.json en data/: se omite la fuente '{fuente}'")
            continue
        try:
            with open(ruta, encoding="utf-8") as f:
                crudos = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[aviso] {ruta.name} no es un JSON válido ({e}): se omite")
            continue

        nuevos = adaptador(crudos)
        # Sin descripción no hay excusa posible: fuera
        nuevos = [r for r in nuevos if r["descripcion"]]
        # Fuera lo que dura demasiado
        nuevos = [r for r in nuevos if duracion_razonable(r)]
        print(f"{fuente:>10}: {len(crudos):4} leídos -> {len(nuevos):4} útiles")
        todos.extend(nuevos)

    antes = len(todos)
    todos = quitar_duplicados(todos)
    print(f"Duplicados eliminados: {antes - len(todos)}")
    return todos


def main():
    datos = homogeneizar()
    print("Por tipo:", dict(Counter(r["tipo"] for r in datos)))
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
    print(f"{len(datos)} registros guardados en {SALIDA.relative_to(DATA.parent)}")


if __name__ == "__main__":
    main()
