import json
from socket import *
import generador
import homogeneizar
import main as pipeline

HOST = ""          # Escucha en todas las tarjetas de red de tu ordenador
PORT = 12000       # Puerto de conexión


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
                    fuente_legible = generador.NOMBRE_FUENTE.get(
                        registro["fuente"], registro["fuente"]
                    )
                    respuesta = {
                        "estado": "ok",
                        "excusa": excusa,
                        "fuente": fuente_legible,
                        "zona": registro.get("zona") or "Valencia",
                        "tipo": registro.get("tipo")
                    }
                print(f"[PETICIÓN] {clientAddress[0]} pidió tipo='{tipo}' -> Enviada excusa.")

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