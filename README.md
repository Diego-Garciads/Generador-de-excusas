# Generador de excusas

Proyecto de Adquisición y Transmisión de Datos (ATD). Genera excusas a partir de datos reales y actuales de Valencia: tráfico (DGT), calles cortadas (Ayuntamiento), Valenbisi y meteorología (AEMET), y rutas de Google Maps.

## Instalación

Requiere Python 3.11 o superior.

```
pip install -r requirements.txt
```

Para descargar los datos de la AEMET hace falta una clave de su API en la variable de entorno `AEMET_API_KEY`. Sin ella, se usan los últimos datos guardados.

La excusa por ruta usa Selenium con Google Chrome, que tiene que estar instalado.

## Uso

La aplicación funciona con un servidor y un cliente, en dos terminales del mismo ordenador (el cliente se conecta a `127.0.0.1:12000`):

```
python src/servidor.py    # carga los datos y espera peticiones en el puerto 12000
python src/cliente.py     # menú para pedir excusas al servidor
```

Desde el cliente se puede pedir una excusa aleatoria o de un tipo, una excusa para una ruta (coordenadas de origen y destino; calcula el trayecto en coche, transporte público y a pie con Google Maps) o actualizar los datos del servidor.

Para ejecutar solo el proceso de datos, sin servidor:

```
python src/main.py                    # descarga los datos, los homogeneiza y genera una excusa
python src/main.py --sin-descargar    # usa los datos ya guardados en data/
python src/main.py --tipo trafico     # excusa de un tipo: trafico, obras, corte_calle, bici, meteo
```

## Estructura

| Carpeta / archivo | Contenido |
|---|---|
| `src/dgt.py`, `src/eventos.py`, `src/valenbisi.py`, `src/aemet_*.py` | Descarga de cada fuente; guardan su JSON en `data/` |
| `src/homogeneizar.py` | Une todas las fuentes en un formato común: `data/homogeneizado.json` |
| `src/generador.py` | Genera una excusa a partir de los datos homogeneizados |
| `src/main.py` | Ejecuta el proceso de datos: descarga, homogeneización y excusa |
| `src/servidor.py` | Servidor TCP: recibe peticiones, genera excusas y actualiza los datos |
| `src/cliente.py` | Cliente de terminal con el menú de opciones |
| `src/rutas_maps.py` | Obtiene rutas de Google Maps con Selenium para las excusas por trayecto |
| `data/` | Datos descargados y homogeneizados |
| `docs/` | Partes del informe |
| `notebooks/` | Exploración de los datos |

## Fuentes de datos

- DGT: incidencias de tráfico
- Ayuntamiento de Valencia (geoportal): obras y cortes de calle
- Valenbisi: disponibilidad de las estaciones
- AEMET OpenData: observaciones meteorológicas. Fuente: © AEMET
- Google Maps: rutas en coche, transporte público y a pie
