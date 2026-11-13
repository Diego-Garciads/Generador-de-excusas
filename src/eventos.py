"""Descarga las ocupaciones de la vía pública de Valencia (obras, fiestas, incidencias...)
y se queda con las que están activas ahora mismo.

Uso:
    python eventos.py            # crea eventos.json
"""
import json
import time
from collections import Counter
from datetime import datetime, timezone

import requests

URL = (
    "https://geoportal.valencia.es/server/rest/services/OPENDATA/Trafico/"
    "MapServer/209/query?where=1=1&outFields=*&f=geojson"
)
POR_PAGINA = 1000


def descargar(url=URL):
    """Descarga todos los registros de la capa.

    Estos servidores ArcGIS limitan cuántos registros devuelve cada petición. Si el
    límite se queda corto, la respuesta trae 'exceededTransferLimit': true y hay que
    seguir pidiendo con 'resultOffset' (desde qué registro empezar).
    """
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    datos = r.json()
    if "error" in datos:
        raise SystemExit(f"Error del servidor: {datos['error']}")

    props = [f["properties"] for f in datos.get("features", [])]
    while datos.get("exceededTransferLimit"):
        r = requests.get(
            url,
            params={"resultOffset": len(props), "resultRecordCount": POR_PAGINA},
            timeout=30,
        )
        r.raise_for_status()
        datos = r.json()
        if "error" in datos:
            raise SystemExit(f"Error al paginar: {datos['error']}")
        nuevos = [f["properties"] for f in datos.get("features", [])]
        if not nuevos:
            break
        props.extend(nuevos)
    return props


def a_iso(ms):
    """Milisegundos desde 1970 -> texto ISO 8601 en UTC. None si no hay valor."""
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


def activo(reg, ahora_ms):
    ini, fin = reg.get("fecha_inicio"), reg.get("fecha_fin")
    return ini is not None and fin is not None and ini <= ahora_ms <= fin


def corta_calle(reg):
    """¿La ocupación corta de verdad la calle (calzada o carril)?

    Quedan fuera las que solo ocupan aparcamiento, acera o zona peatonal,
    que no sirven como excusa para llegar tarde.
    """
    afecta = (reg.get("tipo_afectacion") or "").lower()
    return "calzada" in afecta or "carril" in afecta


def normalizar(reg):
    """Reduce cada ocupación a la estructura común del proyecto."""
    ini, fin = reg.get("fecha_inicio"), reg.get("fecha_fin")
    categoria = (reg.get("tipo_incidencia") or "otro").strip().lower()
    calle = (reg.get("desc_calle") or "").strip().title()
    num = reg.get("numero_policia_origen")
    afecta = (reg.get("tipo_afectacion") or "").strip().lower()
    sitio = f"{calle} {num}".strip() if num else calle
    return {
        "fuente": "eventos",
        "tipo": "corte_calle",
        "categoria": categoria,  # OBRAS o INCIDENCIAS, tal cual viene en origen
        "zona": calle or None,
        "descripcion": f"un corte de calle ({afecta}) en {sitio}",
        "afectacion": afecta or None,
        # En OBRAS suele ser la empresa; en INCIDENCIAS, a ver qué es
        "motivo": (reg.get("desc_incidencia") or "").strip().title() or None,
        "timestamp": a_iso(ini),
        "fin": a_iso(fin),
        # Cuántos días dura en total: las cortas son mejores excusas que las de años
        "duracion_dias": round((fin - ini) / 86_400_000) if ini and fin else None,
    }


def main():
    registros = descargar()
    if not registros:
        raise SystemExit("La capa no ha devuelto registros.")

    ahora_ms = time.time() * 1000
    vigentes = [r for r in registros if activo(r, ahora_ms)]
    print(f"{len(registros)} registros en total, {len(vigentes)} activos ahora")
    print("Tipos (todos):", dict(Counter(r.get("tipo_incidencia") for r in registros)))
    print("Tipos (activos):", dict(Counter(r.get("tipo_incidencia") for r in vigentes)))

    # Para entender qué hay dentro de cada tipo
    for t in sorted({r.get("tipo_incidencia") for r in vigentes if r.get("tipo_incidencia")}):
        grupo = [r for r in vigentes if r.get("tipo_incidencia") == t]
        print(f"\n== {t} ({len(grupo)}) ==")
        print("Afectación:", dict(Counter(r.get("tipo_afectacion") for r in grupo).most_common(8)))
        print("Motivo:", dict(Counter(r.get("desc_incidencia") for r in grupo).most_common(8)))
        durs = sorted(
            (r["fecha_fin"] - r["fecha_inicio"]) / 86_400_000 for r in grupo
        )
        print(f"Duración en días: mínima {durs[0]:.0f}, mediana {durs[len(durs)//2]:.0f}, máxima {durs[-1]:.0f}")
    print()

    cortes = [r for r in vigentes if corta_calle(r)]
    salida = [normalizar(r) for r in cortes]
    print(f"De los {len(vigentes)} activos, {len(salida)} cortan calzada o carril")
    for limite in (7, 30):
        n = sum(1 for e in salida if e["duracion_dias"] is not None and e["duracion_dias"] <= limite)
        print(f"  de esos, {n} duran {limite} días o menos")

    with open("eventos.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)
    print(f"{len(salida)} ocupaciones guardadas en eventos.json")


if __name__ == "__main__":
    main()
