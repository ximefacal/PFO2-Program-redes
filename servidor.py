from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from markupsafe import escape
import sqlite3


# Configuración del servidor
app = Flask(__name__)
DATABASE = "tareas.db"
PUERTO = 5000


def conectar_db():
    # Abre una conexión nueva con la base de datos SQLite.
    # Cada petición usa su propia conexión, así no se comparte entre hilos.
    return sqlite3.connect(DATABASE)


def inicializar_db():
    # Crea la base de datos y la tabla de usuarios si todavía no existen.
    try:
        conexion = conectar_db()
        cursor = conexion.cursor()

        # UNIQUE evita que se registren dos usuarios con el mismo nombre
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                contrasena_hash TEXT NOT NULL
            )
        """)

        conexion.commit()
        conexion.close()

        print("Base de datos inicializada correctamente.")
        return True

    except sqlite3.Error as error:
        print(f"Error al acceder a la base de datos: {error}")
        return False


def obtener_credenciales(datos):
    # Extrae usuario y contraseña del JSON recibido.
    # Se acepta "contraseña" (como pide la consigna) y también "contrasena"
    # por si la terminal tiene problemas con la ñ.
    if datos is None:
        return None, None

    usuario = datos.get("usuario")
    contrasena = datos.get("contraseña") or datos.get("contrasena")

    return usuario, contrasena


def buscar_usuario(usuario):
    # Devuelve el hash de la contraseña del usuario, o None si no existe.
    conexion = conectar_db()
    cursor = conexion.cursor()

    # Consulta parametrizada (?) para evitar inyección SQL
    cursor.execute(
        "SELECT contrasena_hash FROM usuarios WHERE usuario = ?",
        (usuario,)
    )
    fila = cursor.fetchone()

    conexion.close()

    if fila is None:
        return None

    return fila[0]


def verificar_credenciales(usuario, contrasena):
    # Compara la contraseña ingresada con el hash guardado en la base.
    contrasena_hash = buscar_usuario(usuario)

    if contrasena_hash is None:
        return False

    # check_password_hash vuelve a hashear la contraseña ingresada
    # y la compara con el hash almacenado
    return check_password_hash(contrasena_hash, contrasena)


# ---------------------------------------------------------------
# Endpoint 1: Registro de usuarios
# ---------------------------------------------------------------
@app.route("/registro", methods=["POST"])
def registro():
    datos = request.get_json(silent=True)
    usuario, contrasena = obtener_credenciales(datos)

    # Validar que lleguen los dos campos
    if not usuario or not contrasena:
        return jsonify({"error": "Debe enviar 'usuario' y 'contraseña'"}), 400

    # Hashear la contraseña: nunca se guarda en texto plano
    contrasena_hash = generate_password_hash(contrasena)

    conexion = None
    try:
        conexion = conectar_db()
        cursor = conexion.cursor()

        cursor.execute(
            "INSERT INTO usuarios (usuario, contrasena_hash) VALUES (?, ?)",
            (usuario, contrasena_hash)
        )

        conexion.commit()

    except sqlite3.IntegrityError:
        # El nombre de usuario ya existe (restricción UNIQUE)
        return jsonify({"error": "El usuario ya existe"}), 409

    except sqlite3.Error as error:
        print(f"Error al guardar el usuario: {error}")
        return jsonify({"error": "Error en la base de datos"}), 500

    finally:
        # Cerrar siempre la conexión, aunque haya habido un error.
        # Si quedara abierta, bloquearía la base para los próximos registros.
        if conexion is not None:
            conexion.close()

    print(f"Usuario registrado: {usuario}")
    return jsonify({"mensaje": f"Usuario '{usuario}' registrado correctamente"}), 201


# ---------------------------------------------------------------
# Endpoint 2: Inicio de sesión
# ---------------------------------------------------------------
@app.route("/login", methods=["POST"])
def login():
    datos = request.get_json(silent=True)
    usuario, contrasena = obtener_credenciales(datos)

    if not usuario or not contrasena:
        return jsonify({"error": "Debe enviar 'usuario' y 'contraseña'"}), 400

    try:
        valido = verificar_credenciales(usuario, contrasena)

    except sqlite3.Error as error:
        print(f"Error al consultar la base de datos: {error}")
        return jsonify({"error": "Error en la base de datos"}), 500

    if not valido:
        # Mismo mensaje si el usuario no existe o la contraseña es incorrecta,
        # para no darle pistas a un atacante
        return jsonify({"error": "Credenciales inválidas"}), 401

    print(f"Inicio de sesión exitoso: {usuario}")
    return jsonify({
        "mensaje": f"Inicio de sesión exitoso. Bienvenido/a, {usuario}",
        "acceso": "/tareas"
    }), 200


# ---------------------------------------------------------------
# Endpoint 3: Gestión de tareas (protegido con autenticación básica)
# ---------------------------------------------------------------
@app.route("/tareas", methods=["GET"])
def tareas():
    # Autenticación básica HTTP: el cliente envía usuario y contraseña
    # en el encabezado "Authorization" de la petición
    auth = request.authorization

    try:
        valido = auth is not None and verificar_credenciales(auth.username, auth.password)

    except sqlite3.Error as error:
        print(f"Error al consultar la base de datos: {error}")
        return "Error en la base de datos", 500

    if not valido:
        # WWW-Authenticate hace que el navegador muestre la ventana de login
        return (
            "Acceso denegado: debe iniciar sesión.",
            401,
            {"WWW-Authenticate": 'Basic realm="Gestion de Tareas"'}
        )

    # escape() evita que un nombre de usuario con código HTML se ejecute en la página
    nombre = escape(auth.username)

    # HTML de bienvenida
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Gestión de Tareas</title>
        <style>
            body {{ font-family: Arial, sans-serif; background: #f2f4f8;
                   display: flex; justify-content: center; padding-top: 80px; }}
            .tarjeta {{ background: white; padding: 30px 40px; border-radius: 10px;
                       box-shadow: 0 2px 8px rgba(0,0,0,0.15); text-align: center; }}
            h1 {{ color: #2c3e50; }}
        </style>
    </head>
    <body>
        <div class="tarjeta">
            <h1>¡Bienvenido/a, {nombre}!</h1>
            <p>Iniciaste sesión correctamente en el Sistema de Gestión de Tareas.</p>
        </div>
    </body>
    </html>
    """
    return html, 200


# Ejecutar el servidor
if __name__ == "__main__":
    # Si la base de datos no es accesible, el servidor no se inicia
    if inicializar_db():
        app.run(port=PUERTO, debug=True)
