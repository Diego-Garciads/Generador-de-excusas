import json
import random
import unicodedata
from socket import *
import generador
import homogeneizar
import main as pipeline
import rutas_maps

HOST = ""
PORT = 12000


def normalizar_texto(t):
    n = unicodedata.normalize("NFD", (t or "").lower())
    return "".join(c for c in n if unicodedata.category(c) != "Mn")


def cargar_datos_seguro():
    try:
        datos = generador.cargar_datos()
        print(f"[OK] Datos cargados en memoria ({len(datos)} registros).")
        return datos
    except FileNotFoundError:
        print("[AVISO] No existe homogeneizado.json. Descargando datos...")
        pipeline.descargar_todo()
        homogeneizar.main()
        datos = generador.cargar_datos()
        print(f"[OK] Datos cargados en memoria ({len(datos)} registros).")
        return datos


def generar_excusa_por_modo(datos_memoria, modo, info_ruta):
    """Cruza las vías/líneas de un modo (coche, metro, caminando) con datos reales."""
    vias = info_ruta.get("vias", [])
    vias_norm = [normalizar_texto(v) for v in vias if len(v) >= 2]

    # Qué tipos de incidencia del proyecto encajan con cada medio de transporte
    tipos_por_modo = {
        "coche": {"trafico", "obras", "corte_calle"},
        "metro": {"meteo", "corte_calle", "obras"},
        "caminando": {"obras", "corte_calle", "meteo", "bici"},
    }
    tipos_permitidos = tipos_por_modo.get(modo, {"trafico", "obras", "corte_calle", "meteo", "bici"})

    coincidencias = []
    for reg in datos_memoria:
        if reg.get("tipo") not in tipos_permitidos:
            continue
        desc_norm = normalizar_texto(reg.get("descripcion"))
        zona_norm = normalizar_texto(reg.get("zona"))

        for via in vias_norm:
            nucleo = via.replace("calle ", "").replace("avenida ", "").replace("av. ", "").strip()
            if len(nucleo) >= 3 and (nucleo in desc_norm or nucleo in zona_norm):
                coincidencias.append(reg)
                break

    if coincidencias:
        elegido = random.choice(coincidencias)
        desc = elegido["descripcion"]
        if elegido["fuente"] in ("dgt", "eventos"):
            desc = "había " + desc
        return {
            "excusa": f"{random.choice(generador.INICIOS)}{desc} justo en mi trayecto.",
            "coincidencia_exacta": True,
            "fuente": generador.NOMBRE_FUENTE.get(elegido["fuente"], elegido["fuente"]),
            "zona": elegido.get("zona") or "Valencia",
        }

    # Si no hay incidencia exacta en esas calles, elegimos una coherente con ese transporte
    candidatos = [r for r in datos_memoria if r.get("tipo") in tipos_permitidos] or datos_memoria
    elegido = random.choice(candidatos)
    desc = elegido["descripcion"]
    if elegido["fuente"] in ("dgt", "eventos"):
        desc = "había " + desc

    extra_ruta = f" al pasar por {', '.join(vias[:2])}" if vias else ""
    return {
        "excusa": f"{random.choice(generador.INICIOS)}{desc}{extra_ruta}.",
        "coincidencia_exacta": False,
        "fuente": generador.NOMBRE_FUENTE.get(elegido["fuente"], elegido["fuente"]),
        "zona": elegido.get("zona") or "Valencia",
    }


def iniciar_servidor():
    datos_memoria = cargar_datos_seguro()

    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    serverSocket.bind((HOST, PORT))
    serverSocket.listen(5)

    print(f"\n>>> SERVIDOR LISTO en el puerto {PORT} <<<")
    print("Esperando peticiones de usuarios (Ctrl+C para apagar)...\n")

    while True:
        connectionSocket, clientAddress = serverSocket.accept()
        try:
            mensaje_bytes = connectionSocket.recv(4096)
            if not mensaje_bytes:
                connectionSocket.close()
                continue

            peticion = json.loads(mensaje_bytes.decode("utf-8"))
            accion = peticion.get("accion", "pedir_excusa")

            if accion == "pedir_excusa":
                tipo = peticion.get("tipo")
                excusa, registro = generador.generar_excusa(datos_memoria, tipo=tipo)

                if excusa is None:
                    respuesta = {
                        "estado": "sin_datos",
                        "mensaje": f"No hay datos disponibles para el tipo '{tipo}'."
                    }
                else:
                    fuente_legible = generador.NOMBRE_FUENTE.get(registro["fuente"], registro["fuente"])
                    respuesta = {
                        "estado": "ok",
                        "excusa": excusa,
                        "fuente": fuente_legible,
                        "zona": registro.get("zona") or "Valencia",
                        "tipo": registro.get("tipo")
                    }
                print(f"[PETICIÓN] {clientAddress[0]} pidió tipo='{tipo}' -> Enviada excusa.")

            elif accion == "excusa_ruta":
                origen = peticion.get("origen", "").strip()
                destino = peticion.get("destino", "").strip()
                print(f"[RUTA MULTIMODAL] {clientAddress[0]} consulta ({origen}) -> ({destino})...")

                rutas = rutas_maps.obtener_rutas_multimodal(origen, destino, headless=True)
                detalles_modos = {}

                for modo in ("coche", "metro", "caminando"):
                    info = rutas.get(modo, {"duracion": "No disponible", "vias": [], "pasos": []})
                    excusa_info = generar_excusa_por_modo(datos_memoria, modo, info)
                    detalles_modos[modo] = {
                        "duracion": info["duracion"],
                        "vias": info["vias"],
                        "excusa": excusa_info["excusa"],
                        "coincidencia_exacta": excusa_info["coincidencia_exacta"],
                        "fuente": excusa_info["fuente"],
                        "zona": excusa_info["zona"],
                    }

                respuesta = {
                    "estado": "ok",
                    "modos": detalles_modos,
                }
                print(f"[RUTA MULTIMODAL] Enviados itinerarios de coche, metro y caminando a {clientAddress[0]}.")

            elif accion == "actualizar_datos":
                print(f"[ACTUALIZACIÓN] {clientAddress[0]} solicitó recargar datos de APIs...")
                pipeline.descargar_todo()
                homogeneizar.main()
                datos_memoria = generador.cargar_datos()
                respuesta = {
                    "estado": "ok",
                    "mensaje": f"Datos actualizados en el servidor ({len(datos_memoria)} registros)."
                }
                print("[ACTUALIZACIÓN] Completada con éxito.")

            else:
                respuesta = {"estado": "error", "mensaje": "Acción no válida."}

        except Exception as e:
            respuesta = {"estado": "error", "mensaje": f"Error interno: {str(e)}"}

        connectionSocket.sendall(json.dumps(respuesta, ensure_ascii=False).encode("utf-8"))
        connectionSocket.close()


if __name__ == "__main__":
    iniciar_servidor()