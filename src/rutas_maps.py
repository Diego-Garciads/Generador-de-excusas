import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Códigos internos de Google Maps para cada modo de transporte
CODIGOS_MODO = {
    "coche": "0",       # Conducción
    "metro": "3",       # Transporte público
    "caminando": "2",   # A pie
}


def aceptar_cookies_google(driver):
    """Intenta cerrar el aviso de cookies de Google (tanto en la página como en iframes)."""
    xpaths = [
        "//button[contains(., 'Rechazar todo')]",
        "//button[contains(., 'Aceptar todo')]",
        "//form//button",
    ]
    for xp in xpaths:
        try:
            btns = driver.find_elements(By.XPATH, xp)
            for b in btns:
                if b.is_displayed():
                    b.click()
                    time.sleep(1.5)
                    return
        except Exception:
            pass

    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            driver.switch_to.frame(iframe)
            for xp in xpaths:
                btns = driver.find_elements(By.XPATH, xp)
                for b in btns:
                    if b.is_displayed():
                        b.click()
                        driver.switch_to.default_content()
                        time.sleep(1.5)
                        return
            driver.switch_to.default_content()
    except Exception:
        driver.switch_to.default_content()


def limpiar_via(texto_instruccion):
    """Extrae el nombre limpio de la calle, avenida, carretera o línea de metro/bus."""
    # 1. Líneas de metro, tranvía o bus
    match_transporte = re.search(
        r"\b(L[íi]nea\s*\d+|Metrovalencia|L\d+|Bus\s*\d+|EMT\s*\d+|Tranv[íi]a\s*\d+)\b",
        texto_instruccion,
        re.IGNORECASE,
    )
    if match_transporte:
        return match_transporte.group(1).strip()

    # 2. Calles, avenidas, autovías y carreteras
    patrones = [
        r"(?:por|hacia|a|en)\s+((?:C\.|Calle|Av\.|Avenida|Pl\.|Plaza|Autovía|Autopista|Ctra\.|Carretera|Camí|Camino|Gran Vía|Ronda|V-\d+|A-\d+|CV-\d+|N-\d+)[^,\n\(]*)",
        r"\b((?:V-\d+|A-\d+|CV-\d+|N-\d+))\b",
    ]
    for patron in patrones:
        match = re.search(patron, texto_instruccion, re.IGNORECASE)
        if match:
            via = match.group(1).strip()
            # Eliminamos coletillas finales como "hasta tu destino", "en dirección...", etc.
            via = re.split(
                r"\s+(?:en dirección|hacia|durante|hasta tu destino|hasta el destino)\b",
                via,
                flags=re.IGNORECASE,
            )[0]
            return via.strip(" .,-")
    return None


def extraer_info_metro_y_paradas(driver, contenedor):
    """Extrae las líneas de metro/tranvía/bus (desde iconos/spans) y las paradas del trayecto."""
    elementos_metro = []

    # 1. Buscar en atributos aria-label y alt dentro de la tarjeta/panel (ahí guarda Maps "Metro", "Tranvía", "Línea 2", etc.)
    for elem in contenedor.find_elements(By.XPATH, ".//*[@aria-label or @alt]"):
        etiqueta = (elem.get_attribute("aria-label") or elem.get_attribute("alt") or "").strip()
        if not etiqueta:
            continue
        # Ignorar textos genéricos de interfaz
        if any(ign in etiqueta.lower() for ign in ("volver", "compartir", "imprimir", "opciones", "cerrar", "detalles", "a pie")):
            continue
        if any(k in etiqueta.lower() for k in ("metro", "tranvía", "tranvia", "línea", "linea", "autobús", "autobus", "cercanías", "emt")):
            if etiqueta not in elementos_metro:
                elementos_metro.append(etiqueta)

    # 2. Buscar distintivos cortos de línea (ej: "2", "7", "4", "6", "L2", "L7", "C1") en spans
    for span in contenedor.find_elements(By.TAG_NAME, "span"):
        txt = span.text.strip()
        if re.match(r"^(L?\d{1,2}|C\d)$", txt):
            nombre_linea = f"Línea {txt}" if txt.isdigit() else txt
            if nombre_linea not in elementos_metro:
                elementos_metro.append(nombre_linea)

    # 3. Extraer nombres de estaciones/paradas (en el detalle de Maps van justo después de una hora HH:MM)
    lineas_texto = [l.strip() for l in contenedor.text.splitlines() if l.strip()]
    for i, linea in enumerate(lineas_texto):
        if re.match(r"^\d{1,2}:\d{2}$", linea) and i + 1 < len(lineas_texto):
            siguiente = lineas_texto[i + 1]
            # Si la línea siguiente a la hora es el nombre de una estación (no empieza por "Camina" ni números)
            if (
                len(siguiente) > 2
                and not re.match(r"^(Camina|A pie|Toma|Coge|Baja|Subir|\d+|Dirígete|Continúa)", siguiente, re.IGNORECASE)
                and "parada" not in siguiente.lower()
            ):
                parada = f"Estación {siguiente}"
                if parada not in elementos_metro:
                    elementos_metro.append(parada)

    return elementos_metro


def extraer_ruta_modo(driver, origen, destino, modo):
    """Carga la URL directa de Google Maps para un modo concreto y extrae vías/líneas y duración."""
    codigo = CODIGOS_MODO[modo]
    url = f"https://www.google.com/maps/dir/{origen}/{destino}/data=!4m2!4m1!3e{codigo}?hl=es"
    driver.get(url)

    if "consent.google" in driver.current_url:
        aceptar_cookies_google(driver)
        driver.get(url)
    else:
        aceptar_cookies_google(driver)

    wait = WebDriverWait(driver, 12)
    vias = []
    pasos_texto = []
    duracion = "Desconocida"

    try:
        wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@id, 'section-directions-trip') or @data-trip-index]")
            )
        )
        time.sleep(1.5)

        tarjetas = driver.find_elements(
            By.XPATH, "//div[contains(@id, 'section-directions-trip') or @data-trip-index]"
        )
        tarjeta = tarjetas[0]
        lineas_tarjeta = [l.strip() for l in tarjeta.text.splitlines() if l.strip()]

        # 1. Extraer duración (ej: "33 min", "3 h 15 min")
        for l in lineas_tarjeta:
            if re.search(r"^\d+\s*(min|h)\b", l):
                duracion = l
                break

        # 2. Extraer vías del resumen de la tarjeta (ej: "por V-30 y CV-36")
        for l in lineas_tarjeta:
            if l.lower().startswith("por "):
                for parte in re.split(r"\s+y\s+|,\s*", l[4:]):
                    p = parte.strip()
                    if p and p not in vias:
                        vias.append(p)

        # Si es metro, extraemos ya las etiquetas de líneas de la tarjeta resumen
        if modo == "metro":
            for item in extraer_info_metro_y_paradas(driver, tarjeta):
                if item not in vias:
                    vias.append(item)

        # 3. Hacer clic en la tarjeta para abrir el detalle completo
        tarjeta.click()
        time.sleep(2)

        panel = driver.find_element(By.CSS_SELECTOR, "div[role='main']")

        if modo == "metro":
            for item in extraer_info_metro_y_paradas(driver, panel):
                if item not in vias:
                    vias.append(item)
        else:
            for linea in panel.text.splitlines():
                linea = linea.strip()
                if not linea:
                    continue
                pasos_texto.append(linea)
                via = limpiar_via(linea)
                if via and via not in vias:
                    vias.append(via)

    except Exception as e:
        print(f"[MAPS - {modo}] Error: {e}")

    return {
        "duracion": duracion,
        "vias": vias[:12],
        "pasos": pasos_texto[:15],
    }


def obtener_rutas_multimodal(coord_origen, coord_destino, headless=True):
    """Calcula el itinerario para coche, metro y caminando."""
    origen = coord_origen.replace(" ", "")
    destino = coord_destino.replace(" ", "")

    opciones = Options()
    if headless:
        opciones.add_argument("--headless=new")
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument("--window-size=1920,1080")
    opciones.add_argument("--lang=es-ES")
    opciones.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=opciones)
    resultados = {}

    try:
        for modo in ("coche", "metro", "caminando"):
            resultados[modo] = extraer_ruta_modo(driver, origen, destino, modo)
    finally:
        driver.quit()

    return resultados


if __name__ == "__main__":
    res = obtener_rutas_multimodal("39.4370,-0.4655", "39.4811,-0.3408", headless=False)
    for m, info in res.items():
        print(f"\n=== {m.upper()} ({info['duracion']}) ===")
        print("Vías/Líneas:", info["vias"])