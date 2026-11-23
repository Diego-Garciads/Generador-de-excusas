import json
from socket import *

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12000

OPCIONES = {
    "1": None,            # Cualquiera al azar
    "2": "trafico",
    "3": "obras",
    "4": "corte_calle",
    "5": "bici",
    "6": "meteo",
}


def enviar_peticion(payload, timeout=15):
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.settimeout(timeout)
    try:
        clientSocket.connect((SERVER_IP, SERVER_PORT))
        clientSocket.sendall(json.dumps(payload).encode("utf-8"))

        chunks = []
        while True:
            parte = clientSocket.recv(4096)
            if not parte:
                break
            chunks.append(parte)

        return json.loads(b"".join(chunks).decode("utf-8"))
    finally:
        clientSocket.close()


def main():
    print("========================================")
    print("   GENERADOR DE EXCUSAS - CLIENTE")
    print("========================================")
    print("1. Cualquier excusa (aleatoria)")
    print("2. Tráfico (accidentes, retenciones...)")
    print("3. Obras")
    print("4. Corte de calle")
    print("5. Valenbisi (sin bicis / sin huecos)")
    print("6. Meteorología (lluvia / viento)")
    print("7. Excusa por RUTA (Coche, Metro y Caminando)")
    print("9. [ADMIN] Actualizar datos en el servidor")
    print("0. Salir")

    while True:
        opcion = input("\nElige una opción (0-9): ").strip()

        if opcion == "0":
            print("Cerrando cliente...")
            break

        if opcion == "7":
            print("\nIntroduce las coordenadas en formato latitud,longitud (ej: 39.4699,-0.3763)")
            origen = input("Coordenadas de INICIO: ").strip()
            destino = input("Coordenadas de DESTINO: ").strip()

            if not origen or not destino:
                print("Debes introducir ambas coordenadas.")
                continue

            print("Calculando rutas en coche, metro y caminando en Google Maps (espera ~10-15s)...")
            try:
                res = enviar_peticion({
                    "accion": "excusa_ruta",
                    "origen": origen,
                    "destino": destino
                }, timeout=60)

                if res.get("estado") == "ok":
                    modos = res.get("modos", {})
                    titulos = {
                        "coche": "EN COCHE",
                        "metro": "EN METRO / TRANSPORTE PÚBLICO",
                        "caminando": "CAMINANDO",
                    }
                    for clave in ("coche", "metro", "caminando"):
                        datos = modos.get(clave, {})
                        vias = datos.get("vias", [])
                        print("\n" + "-" * 50)
                        print(f"[{titulos[clave]}] Duración estimada: {datos.get('duracion')}")
                        print(f"Vías / Líneas: {', '.join(vias) if vias else 'No especificadas'}")
                        if datos.get("coincidencia_exacta"):
                            print("[!] ¡Incidencia real detectada justo en este itinerario!")
                        print(f"EXCUSA: {datos.get('excusa')}")
                        print(f"(Fuente: {datos.get('fuente')} | Zona: {datos.get('zona')})")
                    print("-" * 50)
                else:
                    print(f"\nAVISO: {res.get('mensaje')}")
            except Exception as e:
                print(f"\n[ERROR] Fallo al calcular rutas: {e}")
            continue

        if opcion == "9":
            print("Conectando con el servidor para descargar y actualizar datos...")
            try:
                res = enviar_peticion({"accion": "actualizar_datos"}, timeout=120)
                print(">>", res.get("mensaje"))
            except Exception as e:
                print(f"[ERROR] No se pudo actualizar: {e}")
            continue

        if opcion not in OPCIONES:
            print("Opción no válida. Elige un número del menú.")
            continue

        try:
            res = enviar_peticion({
                "accion": "pedir_excusa",
                "tipo": OPCIONES[opcion]
            })

            if res.get("estado") == "ok":
                print(f"\nEXCUSA: {res['excusa']}")
                print(f"(Fuente: {res['fuente']} | Zona: {res['zona']} | Categoría: {res['tipo']})")
            else:
                print(f"\nAVISO: {res.get('mensaje')}")

        except ConnectionRefusedError:
            print(f"\n[ERROR] No hay conexión con {SERVER_IP}:{SERVER_PORT}. Asegúrate de que servidor.py está encendido.")
        except Exception as e:
            print(f"\n[ERROR] Fallo de comunicación: {e}")


if __name__ == "__main__":
    main()