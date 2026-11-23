import json
from socket import *

# IMPORTANTE: Si el usuario está en OTRO ordenador, cambia "127.0.0.1"
# por la IP de tu ordenador servidor (ej. "192.168.1.45")
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


def enviar_peticion(payload, timeout=10):
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
    print("9. [ADMIN] Actualizar datos en el servidor")
    print("0. Salir")

    while True:
        opcion = input("\nElige una opción (0-9): ").strip()

        if opcion == "0":
            print("Cerrando cliente...")
            break

        if opcion == "9":
            print("Conectando con el servidor para descargar y actualizar datos (espera unos segundos)...")
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