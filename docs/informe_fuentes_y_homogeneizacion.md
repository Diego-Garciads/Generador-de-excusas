# Fuentes de datos, homogeneización y programa principal (parte de Diego García García)

## 1. Fuentes de datos

Se usan tres fuentes de datos abiertos, todas de la ciudad de Valencia o su entorno. Cada una tiene su propio script en `src/`, que descarga los datos con el paquete `requests` (petición HTTP GET), se queda con los campos útiles y los guarda en un JSON en `data/`.

| Fuente | Organismo | Formato | Script | Qué aporta como excusa |
|---|---|---|---|---|
| Incidencias de tráfico | DGT (Punto de Acceso Nacional) | XML (estándar DATEX II) | `src/dgt.py` | Accidentes, vehículos averiados, obstáculos, retenciones y obras en carretera |
| Ocupaciones de la vía pública | Ayuntamiento de Valencia (Geoportal, ArcGIS) | GeoJSON | `src/eventos.py` | Calles cortadas por obras u otras incidencias |
| Disponibilidad de Valenbisi | Ayuntamiento de Valencia (datos abiertos) | JSON | `src/valenbisi.py` | Estaciones sin bicis, sin huecos para dejarla o cerradas |

### 1.1 DGT (`dgt.py`)
- Descarga el fichero XML con todas las incidencias de España.
- El XML usa *namespaces* (prefijos en las etiquetas). Para no depender de ellos, se compara solo el nombre de la etiqueta (por ejemplo, `roadName`).
- De cada incidencia (`<situationRecord>`) se extraen: tipo, causa, carretera, punto kilométrico, municipio, provincia y fechas de inicio y fin.
- Se clasifica cada incidencia en un tipo de excusa (accidente, obras, retención…) mediante una lista de reglas ordenada.
- Se filtra por provincia de Valencia.

### 1.2 Ocupaciones de la vía pública (`eventos.py`)
- Consulta un servicio ArcGIS del Geoportal municipal (`where=1=1`, todos los campos, formato GeoJSON).
- Como el servidor limita el número de registros por petición, se implementa **paginación** (`exceededTransferLimit` y `resultOffset`).
- Las fechas vienen en milisegundos desde 1970 y se convierten a ISO 8601.
- Filtros: solo ocupaciones **activas en el momento de la consulta** y solo las que **cortan la calzada o un carril** (las que solo ocupan acera o aparcamiento no sirven de excusa).
- La descripción técnica del Ayuntamiento se traduce a lenguaje natural: `100% calzada` → "un corte total de la calle", `1 carril` → "un carril cortado", `C/` → "la calle", etc. Si la calle no tiene número (la fuente pone `0`), no se muestra.

### 1.3 Valenbisi (`valenbisi.py`)
- Descarga el estado de todas las estaciones en una sola petición.
- Normaliza los campos: dirección, bicis libres, huecos libres, total, si está abierta (convertido de `"T"`/`"F"` a booleano) y fecha de actualización.
- Comprueba la antigüedad de los datos y avisa si no son recientes.

Todos los scripts guardan su resultado en la carpeta `data/` del proyecto, independientemente de desde dónde se ejecuten.

[CAPTURA: ejecución de los scripts de descarga]

## 2. Homogeneización y filtrado (`homogeneizar.py`)

Cada fuente entrega los datos con una estructura distinta (nombres de campos, formatos de fecha, nivel de detalle). Para que el generador de excusas pueda usarlos todos por igual, `src/homogeneizar.py` los traduce a una **estructura común** y guarda el resultado en `data/homogeneizado.json`.

### 2.1 Estructura común

| Campo | Contenido |
|---|---|
| `fuente` | De dónde viene el dato (`dgt`, `eventos`, `valenbisi`…) |
| `tipo` | Categoría de excusa común a todas las fuentes: `trafico`, `obras`, `corte_calle`, `bici`… |
| `subtipo` | Detalle dentro de la categoría (por ejemplo, `accidente` o `sin_bicis`) |
| `zona` | Lugar, en texto |
| `descripcion` | Frase lista para usar en la excusa |
| `inicio`, `fin` | Fechas en ISO 8601 con la zona horaria de Madrid |
| `detalles` | Campos propios de cada fuente que no son comunes |

### 2.2 Funcionamiento
- Hay una función por fuente (`desde_dgt`, `desde_eventos`, `desde_valenbisi`) que traduce sus campos a la estructura común. Para añadir una fuente nueva basta con escribir su función y añadirla al diccionario `ADAPTADORES`.
- Si falta el JSON de una fuente o está mal formado, el script avisa y continúa con las demás (`try/except`).

### 2.3 Filtrado y limpieza
- **Ámbito geográfico:** de la DGT solo se conservan las incidencias de València y su área metropolitana (municipios de l'Horta).
- **Fechas unificadas:** las tres fuentes usaban formatos distintos (con zona horaria, en UTC y sin zona horaria). Todas se convierten a hora de Madrid. En el Geoportal la hora local viene marcada como UTC, y se corrige.
- **Topónimos bilingües:** `Alboraia/Alboraya` → `Alboraya`, para que todos los nombres vayan en el mismo idioma.
- **Valenbisi:** solo se conservan las estaciones que sirven de excusa (vacías, llenas o cerradas), y se descartan las que llevan mucho tiempo sin actualizarse (datos congelados).
- **Duración:** se descarta todo lo que dura más de 60 días. Unas obras que llevan meses no son una excusa creíble.
- **AEMET:** de cada estación meteorológica se toma la observación más reciente y solo genera excusa si llueve (≥ 0,5 mm en la última hora) o hay rachas de viento de 50 km/h o más.
- **Duplicados:** se eliminan los registros repetidos.
- Se descarta cualquier registro sin descripción.

### 2.4 Resultado

El número de registros cambia en cada ejecución, porque los datos son en tiempo real. En cada ejecución el script muestra, para cada fuente, cuántos registros ha leído y cuántos son útiles como excusa.

[CAPTURA: ejecución de `homogeneizar.py`]
[CAPTURA: fragmento de `data/homogeneizado.json`]

## 3. Programa principal y generador de excusas

### 3.1 Generador (`generador.py`)
Versión sencilla del generador, pensada para demostrar el flujo completo:
1. Lee `data/homogeneizado.json`.
2. Elige al azar un **tipo** de excusa (tráfico, obras, bici, meteo…) y después un dato real de ese tipo. Así todos los tipos aparecen con la misma frecuencia, aunque de alguno haya muchos más datos.
3. Monta la frase con un inicio elegido al azar ("Perdona el retraso: …") y la descripción del dato, e indica la fuente para que la excusa sea comprobable.

Se puede pedir un tipo concreto: `python src/generador.py --tipo bici`.

### 3.2 Programa principal (`main.py`)
Ejecuta todo el proyecto con un solo comando (`python src/main.py`):
1. **Descarga:** lanza cada script de descarga (DGT, Ayuntamiento, Valenbisi, AEMET). Si alguno falla, lo indica y continúa con los últimos datos guardados de esa fuente.
2. **Homogeneización:** genera `data/homogeneizado.json`.
3. **Excusa:** genera y muestra una excusa.

Opciones: `--sin-descargar` (usa los datos guardados) y `--tipo` (excusa de un tipo concreto).

[CAPTURA: ejecución completa de `main.py`]

## 4. Uso de IA en esta parte

Modelo utilizado: **Claude Opus 5.5** (Anthropic).

- Explicación y revisión del código de los tres scripts de extracción, con propuestas de mejora.
- Revisión del proyecto frente a la rúbrica y las prácticas de la asignatura.
- Redacción de `src/homogeneizar.py` (estructura común, adaptadores por fuente y filtros), que después he revisado, ejecutado y subido al repositorio.
- Redacción de `src/generador.py` y `src/main.py`, y de las mejoras de las frases de las excusas, que he revisado, probado y subido al repositorio.
- Borrador de esta sección del informe.
- Apoyo en la programación de los scripts de extracción (dgt.py, eventos.py y valenbisi.py). La búsqueda y selección de las fuentes de datos y de sus APIs la realicé yo; el código generado con ayuda de la IA lo revisé y probé con los datos reales.

