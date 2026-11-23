import os
import requests
import json

API_KEY  = os.environ["AEMET_API_KEY"] # guardada como variable de entorno en el terminal
BASE_URL = "https://opendata.aemet.es/opendata/api"
HEADERS = {"api_key" : API_KEY}


def llamada_control(endpoint):

    r = requests.get(f"{BASE_URL}/{endpoint}", headers=HEADERS, timeout=10)
    r.raise_for_status() # nivel 1: código HTTP

    control = r.json()

    estado = control.get("estado")
    if estado != 200: # nivel 2: estado de la API
        raise RuntimeError(estado, control.get("descripcion"))
    
    return control


def llamada_general(url):

    r = requests.get(url, timeout=30)
    r.raise_for_status()

    try:
        texto = r.content.decode("utf-8")
    except UnicodeDecodeError:
        texto = r.content.decode("latin-1")
    return json.loads(texto) # guardamos los datos en una lista de diccionarios


def llamada_datos(endpoint, metadatos=False):
    control = llamada_control(endpoint)
    url1, url2 = control["datos"], control["metadatos"]
    
    if metadatos == True:
        return llamada_general(url1), llamada_general(url2)["campos"]

    return llamada_general(url1)


def llamada_metadatos(endpoint):

    url = llamada_control(endpoint)["metadatos"] 

    return llamada_general(url)["campos"]
