"""Repositorios del gateway contra PostgreSQL.

Diferencias con la versión Oracle que hay que tener presentes:
  - Los parámetros son posicionales `%s` (psycopg2), no `:nombre` (oracledb).
  - `usuarios.id` es `uuid`: se pasa el objeto `uuid.UUID`, nunca `.bytes`.
    `refresh_tokens.user_id` y `codigos_respaldo.user_id` son `varchar(36)`,
    esos sí van como texto.
  - Los booleanos son `boolean`, no `NUMBER(1)`.
"""

import uuid

from gateway.infrastructure.pg_pool import adquirir_conexion

_CAMPOS_USUARIO = (
    "id, email, password_hash, nombre, apellido, rol, activo, "
    "auth_provider, google_sub, mfa_secret, mfa_activo"
)


def _uuid_a_texto(valor):
    if valor is None:
        return None
    if isinstance(valor, bytes):
        return str(uuid.UUID(bytes=valor))
    return str(valor)


def _fila_a_usuario(fila, descripcion):
    if fila is None:
        return None
    columnas = [d[0].lower() for d in descripcion]
    usuario = dict(zip(columnas, fila))
    usuario["id"] = _uuid_a_texto(usuario["id"])
    usuario["mfa_activo"] = bool(usuario.get("mfa_activo"))
    return usuario


def buscar_usuario_por_email(email):
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                f"SELECT {_CAMPOS_USUARIO} FROM usuarios WHERE LOWER(email) = LOWER(%s)",
                (email,),
            )
            return _fila_a_usuario(cursor.fetchone(), cursor.description)


def buscar_usuario_por_id(user_id):
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                f"SELECT {_CAMPOS_USUARIO} FROM usuarios WHERE id = %s",
                (uuid.UUID(user_id),),
            )
            return _fila_a_usuario(cursor.fetchone(), cursor.description)


def crear_usuario(email, password_hash, nombre, apellido, telefono, rol="cliente"):
    """Crea un usuario nuevo con rol fijo (nunca admin) y lo devuelve."""
    nuevo_id = uuid.uuid4()
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO usuarios
                    (id, email, password_hash, nombre, apellido, telefono, rol, activo, creado_en)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, true, now())
                """,
                (
                    nuevo_id, email, password_hash, nombre, apellido,
                    telefono, rol,
                ),
            )
    return {
        "id": str(nuevo_id),
        "email": email,
        "nombre": nombre,
        "apellido": apellido,
        "rol": rol,
    }


def actualizar_password(user_id, password_hash):
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "UPDATE usuarios SET password_hash = %s WHERE id = %s",
                (password_hash, uuid.UUID(user_id)),
            )


def guardar_refresh(jti, user_id, expira_en, ip, user_agent):
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO refresh_tokens (jti, user_id, expira_en, revocado, ip, user_agent)
                VALUES (%s, %s, %s, false, %s, %s)
                """,
                (jti, user_id, expira_en, ip, user_agent),
            )


def buscar_refresh(jti):
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT jti, user_id, expira_en, revocado
                FROM refresh_tokens
                WHERE jti = %s
                """,
                (jti,),
            )
            fila = cursor.fetchone()
            if fila is None:
                return None
            columnas = [d[0].lower() for d in cursor.description]
            registro = dict(zip(columnas, fila))
            registro["revocado"] = bool(registro["revocado"])
            return registro


def revocar_refresh(jti):
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "UPDATE refresh_tokens SET revocado = true WHERE jti = %s",
                (jti,),
            )


def revocar_tokens_de_usuario(user_id):
    # refresh_tokens.user_id es varchar(36), no uuid: va como texto.
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "UPDATE refresh_tokens SET revocado = true WHERE user_id = %s",
                (user_id,),
            )


def registrar_log(evento, user_id, ip, detalle):
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO logs_seguridad (evento, user_id, ip, detalle)
                VALUES (%s, %s, %s, %s)
                """,
                (evento, user_id, ip, detalle),
            )


def guardar_codigo(email, codigo_hash, expira_en):
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "DELETE FROM codigos_verificacion WHERE LOWER(email) = LOWER(%s) AND usado = false",
                (email,),
            )
            cursor.execute(
                """
                INSERT INTO codigos_verificacion (email, codigo_hash, expira_en)
                VALUES (%s, %s, %s)
                """,
                (email, codigo_hash, expira_en),
            )


def buscar_codigo(email):
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT email, codigo_hash, expira_en, usado
                FROM codigos_verificacion
                WHERE LOWER(email) = LOWER(%s) AND usado = false
                ORDER BY creado_en DESC
                """,
                (email,),
            )
            fila = cursor.fetchone()
            if fila is None:
                return None
            columnas = [d[0].lower() for d in cursor.description]
            registro = dict(zip(columnas, fila))
            registro["usado"] = bool(registro["usado"])
            return registro


def marcar_codigo_usado(email):
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "UPDATE codigos_verificacion SET usado = true WHERE LOWER(email) = LOWER(%s)",
                (email,),
            )


def buscar_bloqueo(clave, tipo):
    """Retorna el registro de bloqueos de una clave (email o ip) + tipo."""
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT clave, tipo, fallos, nivel, bloqueo_hasta
                FROM bloqueos_login
                WHERE LOWER(clave) = LOWER(%s) AND tipo = %s
                """,
                (clave, tipo),
            )
            fila = cursor.fetchone()
            if fila is None:
                return None
            columnas = [d[0].lower() for d in cursor.description]
            return dict(zip(columnas, fila))


def guardar_o_actualizar_bloqueo(clave, tipo, fallos, nivel, bloqueo_hasta):
    """Inserta o actualiza un contador de fallos/bloqueo para una clave+tipo.

    Traduccion del `MERGE` de Oracle. El predicado original comparaba
    `LOWER(t.clave) = LOWER(s.clave)`, asi que el indice de conflicto es sobre
    `lower(clave)`: `ON CONFLICT` exige un indice unico y coincide con la
    semántica case-insensitive del original.
    """
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO bloqueos_login
                    (clave, tipo, fallos, nivel, bloqueo_hasta, actualizado_en)
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (lower(clave), tipo) DO UPDATE
                SET fallos = EXCLUDED.fallos,
                    nivel = EXCLUDED.nivel,
                    bloqueo_hasta = EXCLUDED.bloqueo_hasta,
                    actualizado_en = now()
                """,
                (clave, tipo, fallos, nivel, bloqueo_hasta),
            )


def limpiar_bloqueo(clave, tipo):
    """Borra el contador de fallos de una clave+tipo (login exitoso)."""
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "DELETE FROM bloqueos_login WHERE LOWER(clave) = LOWER(%s) AND tipo = %s",
                (clave, tipo),
            )


def guardar_codigos_respaldo(user_id, codigos_hash):
    """Reemplaza los códigos de respaldo de un usuario por la lista nueva."""
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            # codigos_respaldo.user_id es varchar(36): va como texto.
            cursor.execute(
                "DELETE FROM codigos_respaldo WHERE user_id = %s",
                (user_id,),
            )
            for codigo_hash in codigos_hash:
                cursor.execute(
                    """
                    INSERT INTO codigos_respaldo (user_id, codigo_hash)
                    VALUES (%s, %s)
                    """,
                    (user_id, codigo_hash),
                )


def buscar_codigo_respaldo_activo(user_id):
    """Retorna los códigos de respaldo no usados de un usuario."""
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id, codigo_hash
                FROM codigos_respaldo
                WHERE user_id = %s AND usado = false
                ORDER BY id
                """,
                (user_id,),
            )
            filas = cursor.fetchall()
            if not filas:
                return []
            columnas = [d[0].lower() for d in cursor.description]
            return [dict(zip(columnas, fila)) for fila in filas]


def marcar_codigo_respaldo_usado(codigo_id):
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "UPDATE codigos_respaldo SET usado = true WHERE id = %s",
                (codigo_id,),
            )


def actualizar_mfa(user_id, mfa_secret, mfa_activo):
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                UPDATE usuarios
                SET mfa_secret = %s, mfa_activo = %s
                WHERE id = %s
                """,
                (mfa_secret, bool(mfa_activo), uuid.UUID(user_id)),
            )


def buscar_usuario_por_google_sub(google_sub):
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                f"SELECT {_CAMPOS_USUARIO} FROM usuarios WHERE google_sub = %s",
                (google_sub,),
            )
            return _fila_a_usuario(cursor.fetchone(), cursor.description)


def vincular_google(user_id, google_sub):
    """Asocia una cuenta Google a un usuario existente y actualiza auth_provider."""
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                UPDATE usuarios
                SET google_sub = %s, auth_provider = 'google'
                WHERE id = %s
                """,
                (google_sub, uuid.UUID(user_id)),
            )


def crear_usuario_google(email, google_sub, nombre, apellido, password_hash):
    """Crea un usuario nuevo autenticado via Google (password_hash placeholder)."""
    nuevo_id = uuid.uuid4()
    with adquirir_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO usuarios
                    (id, email, password_hash, nombre, apellido, rol, activo,
                     auth_provider, google_sub, creado_en)
                VALUES
                    (%s, %s, %s, %s, %s, 'cliente', true,
                     'google', %s, now())
                """,
                (nuevo_id, email, password_hash, nombre, apellido, google_sub),
            )
    return {
        "id": str(nuevo_id),
        "email": email,
        "nombre": nombre,
        "apellido": apellido,
        "rol": "cliente",
    }