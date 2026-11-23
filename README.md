# Generador de excusas

Proyecto de Adquisición y Transmisión de Datos (ATD). Genera excusas a partir de datos reales y actuales de Valencia: tráfico (DGT), calles cortadas (Ayuntamiento), Valenbisi y meteorología (AEMET).

## Instalación

```
pip install -r requirements.txt
```

Para descargar los datos de la AEMET hace falta una clave de su API en la variable de entorno `AEMET_API_KEY`. Sin ella, se usan los últimos datos guardados.

## Uso

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
| `src/main.py` | Ejecuta todo el proceso |
| `data/` | Datos descargados y homogeneizados |
| `docs/` | Partes del informe |
| `notebooks/` | Exploración de los datos |
