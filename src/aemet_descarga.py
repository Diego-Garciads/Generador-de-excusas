import json
import time
from datetime import datetime, timezone
from pathlib import Path

from requests.exceptions import HTTPError, RequestException 

from aemet_api import llamada_datos, llamada_metadatos


estaciones = {'8409X': 'LLÍRIA',
              '8414A': 'VALENCIA AEROPUERTO',
              '8416': 'VALÈNCIA',
              '8416X': 'VALENCIA, UPV',
              '8416Y': 'VALÈNCIA, VIVEROS',
              '8446Y': 'SAGUNT/SAGUNTO'
}


def descargar_datos_lluvia_actual(estaciones, reintentos=3, espera=60):

    datos_lluvia = []
    fallidas = [] # (estación, motivo) en vez de solo imprimir por pantalla
    metadatos = llamada_metadatos("/observacion/convencional/todas")

    for est in estaciones:
        endpoint = f"/observacion/convencional/datos/estacion/{est}"

        for intento in range(reintentos):
            try:
                datos_lluvia.extend(llamada_datos(endpoint))
                break # en caso de no haber problemas salimos del bucle de reintentos

            except HTTPError as e: # para acortar 
                if e.response.status_code == 429: # limite de llamadas ha sido alcanzado: toca esperar
                    time.sleep(espera)
                    continue
                fallidas.append((est, e.response.status_code))
                break

            except RuntimeError as e:
                if e.args[0] == 429:          # límite avisado dentro del JSON
                    time.sleep(espera)
                    continue
                fallidas.append((est, e.args))
                break

            except RequestException: # Claude Opus 5.5 (bajo)
                time.sleep(5)

        else:
            fallidas.append((est, "reintentos agotados"))



    return datos_lluvia, metadatos, fallidas


if __name__ == "__main__":

    datos_lluvia, metadatos, fallidas = descargar_datos_lluvia_actual(estaciones)

    CARPETA = Path("data")
    CARPETA.mkdir(exist_ok=True)                      # crea la carpeta si no existe

    momento_descarga = datetime.now(timezone.utc)
    marca = momento_descarga.strftime("%Y%m%dT%H%MZ") 
    ruta = CARPETA / f"aemet_obs_{marca}.json"

    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos_lluvia, f, ensure_ascii=False, indent=2)

    # comprobación: lo que se lee es igual a lo que se ha guardado Claude Opus 5.5 (bajo)
    with open(ruta, encoding="utf-8") as f:
        recargado = json.load(f)
    assert recargado == datos_lluvia, "El archivo no coincide con los datos descargados"
    print(f"Guardado: {ruta} ({len(recargado)} registros)")
