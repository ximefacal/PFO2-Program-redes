import requests


# Configuración del cliente: dirección de la API
URL_SERVIDOR = "http://localhost:5000"


def pedir_credenciales():
    # Pide usuario y contraseña por consola.
    usuario = input("Usuario: ").strip()
    contrasena = input("Contraseña: ").strip()
    return usuario, contrasena


def registrar_usuario():
    # Envía un POST /registro con los datos en formato JSON.
    usuario, contrasena = pedir_credenciales()

    respuesta = requests.post(
        f"{URL_SERVIDOR}/registro",
        json={"usuario": usuario, "contraseña": contrasena}
    )

    mostrar_respuesta(respuesta)


def iniciar_sesion():
    # Envía un POST /login. Si es correcto, devuelve las credenciales
    # para poder usarlas después en GET /tareas.
    usuario, contrasena = pedir_credenciales()

    respuesta = requests.post(
        f"{URL_SERVIDOR}/login",
        json={"usuario": usuario, "contraseña": contrasena}
    )

    mostrar_respuesta(respuesta)

    if respuesta.status_code == 200:
        return usuario, contrasena

    return None


def ver_tareas(credenciales):
    # Envía un GET /tareas usando autenticación básica HTTP.
    if credenciales is None:
        print("Primero tenés que iniciar sesión (opción 2).")
        return

    respuesta = requests.get(f"{URL_SERVIDOR}/tareas", auth=credenciales)

    print(f"Código de estado: {respuesta.status_code}")
    print(respuesta.text)


def mostrar_respuesta(respuesta):
    # Muestra el código HTTP y el mensaje JSON que devolvió el servidor.
    print(f"Código de estado: {respuesta.status_code}")

    datos = respuesta.json()
    if "mensaje" in datos:
        print(datos["mensaje"])
    else:
        print(f"Error: {datos['error']}")


def mostrar_menu():
    print("\n===== Sistema de Gestión de Tareas =====")
    print("1. Registrarse")
    print("2. Iniciar sesión")
    print("3. Ver tareas")
    print("4. Salir")
    return input("Elegí una opción: ").strip()


# ****Función principal del cliente.****
def main():
    # Guarda las credenciales después de un login exitoso
    credenciales = None

    while True:
        opcion = mostrar_menu()

        try:
            if opcion == "1":
                registrar_usuario()
            elif opcion == "2":
                credenciales = iniciar_sesion()
            elif opcion == "3":
                ver_tareas(credenciales)
            elif opcion == "4":
                print("Hasta luego.")
                break
            else:
                print("Opción inválida.")

        except requests.exceptions.ConnectionError:
            print("No se pudo conectar al servidor.")
            print("Verificá que servidor.py esté ejecutándose.")


# Ejecutar el cliente
if __name__ == "__main__":
    main()
