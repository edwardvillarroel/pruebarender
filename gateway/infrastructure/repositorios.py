import uuid

from gateway.infrastructure.oracle_pool import adquirir_conexion

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
        cursor = conexion.cursor()
        cursor.execute(
            f"SELECT {_CAMPOS_USUARIO} FROM usuarios WHERE LOWER(email) = LOWER(:email)",
            email=email,
        )
        return _fila_a_usuario(cursor.fetchone(), cursor.description)


def buscar_usuario_por_id(user_id):
    with adquirir_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            f"SELECT {_CAMPOS_USUARIO} FROM usuarios WHERE id = :user_id",
            user_id=uuid.UUID(user_id).bytes,
        )
        return _fila_a_usuario(cursor.fetchone(), cursor.description)


def crear_usuario(email, password_hash, nombre, apellido, telefono, rol="cliente"):
    """Crea un usuario nuevo con rol fijo (nunca admin) y lo devuelve."""
    nuevo_id = uuid.uuid4()
    with adquirir_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO usuarios
                (id, email, password_hash, nombre, apellido, telefono, rol, activo, creado_en)
            VALUES
                (:id, :email, :password_hash, :nombre, :apellido, :telefono, :rol, 1, CURRENT_TIMESTAMP)
            """,
            id=nuevo_id.bytes,
            email=email,
            password_hash=password_hash,
            nombre=nombre,
            apellido=apellido,
            telefono=telefono,
            rol=rol,
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
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE usuarios SET password_hash = :password_hash WHERE id = :user_id",
            password_hash=password_hash,
            user_id=uuid.UUID(user_id).bytes,
        )


def guardar_refresh(jti, user_id, expira_en, ip, user_agent):
    with adquirir_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO refresh_tokens (jti, user_id, expira_en, revocado, ip, user_agent)
            VALUES (:jti, :user_id, :expira_en, 0, :ip, :user_agent)
            """,
            jti=jti, user_id=user_id, expira_en=expira_en, ip=ip, user_agent=user_agent,
        )


def buscar_refresh(jti):
    with adquirir_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT jti, user_id, expira_en, revocado
            FROM refresh_tokens
            WHERE jti = :jti
            """,
            jti=jti,
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
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE refresh_tokens SET revocado = 1 WHERE jti = :jti",
            jti=jti,
        )


def revocar_tokens_de_usuario(user_id):
    with adquirir_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE refresh_tokens SET revocado = 1 WHERE user_id = :user_id",
            user_id=user_id,
        )


def registrar_log(evento, user_id, ip, detalle):
    with adquirir_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO logs_seguridad (evento, user_id, ip, detalle)
            VALUES (:evento, :user_id, :ip, :detalle)
            """,
            evento=evento, user_id=user_id, ip=ip, detalle=detalle,
        )


def guardar_codigo(email, codigo_hash, expira_en):
    with adquirir_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            "DELETE FROM codigos_verificacion WHERE LOWER(email) = LOWER(:email) AND usado = 0",
            email=email,
        )
        cursor.execute(
            """
            INSERT INTO codigos_verificacion (email, codigo_hash, expira_en)
            VALUES (:email, :codigo_hash, :expira_en)
            """,
            email=email, codigo_hash=codigo_hash, expira_en=expira_en,
        )


def buscar_codigo(email):
    with adquirir_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT email, codigo_hash, expira_en, usado
            FROM codigos_verificacion
            WHERE LOWER(email) = LOWER(:email) AND usado = 0
            ORDER BY creado_en DESC
            """,
            email=email,
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
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE codigos_verificacion SET usado = 1 WHERE LOWER(email) = LOWER(:email)",
            email=email,
        )


def buscar_bloqueo(clave, tipo):
    """Retorna el registro de bloqueos de una clave (email o ip) + tipo."""
    with adquirir_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT clave, tipo, fallos, nivel, bloqueo_hasta
            FROM bloqueos_login
            WHERE LOWER(clave) = LOWER(:clave) AND tipo = :tipo
            """,
            clave=clave,
            tipo=tipo,
        )
        fila = cursor.fetchone()
        if fila is None:
            return None
        columnas = [d[0].lower() for d in cursor.description]
        return dict(zip(columnas, fila))


def guardar_o_actualizar_bloqueo(clave, tipo, fallos, nivel, bloqueo_hasta):
    """Inserta o actualiza un contador de fallos/bloqueo para una clave+tipo."""
    with adquirir_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            """
            MERGE INTO bloqueos_login t
            USING (SELECT :clave AS clave, :tipo AS tipo FROM dual) s
            ON (LOWER(t.clave) = LOWER(s.clave) AND t.tipo = s.tipo)
            WHEN MATCHED THEN
                UPDATE SET fallos = :fallos, nivel = :nivel,
                           bloqueo_hasta = :bloqueo_hasta,
                           actualizado_en = SYSTIMESTAMP
            WHEN NOT MATCHED THEN
                INSERT (clave, tipo, fallos, nivel, bloqueo_hasta)
                VALUES (:clave, :tipo, :fallos, :nivel, :bloqueo_hasta)
            """,
            clave=clave,
            tipo=tipo,
            fallos=fallos,
            nivel=nivel,
            bloqueo_hasta=bloqueo_hasta,
        )


def limpiar_bloqueo(clave, tipo):
    """Borra el contador de fallos de una clave+tipo (login exitoso)."""
    with adquirir_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            "DELETE FROM bloqueos_login WHERE LOWER(clave) = LOWER(:clave) AND tipo = :tipo",
            clave=clave,
            tipo=tipo,
        )


def guardar_codigos_respaldo(user_id, codigos_hash):
    """Reemplaza los códigos de respaldo de un usuario por la lista nueva."""
    with adquirir_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            "DELETE FROM codigos_respaldo WHERE user_id = :user_id",
            user_id=user_id,
        )
        for codigo_hash in codigos_hash:
            cursor.execute(
                """
                INSERT INTO codigos_respaldo (user_id, codigo_hash)
                VALUES (:user_id, :codigo_hash)
                """,
                user_id=user_id,
                codigo_hash=codigo_hash,
            )


def buscar_codigo_respaldo_activo(user_id):
    """Retorna los códigos de respaldo no usados de un usuario."""
    with adquirir_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT id, user_id, codigo_hash
            FROM codigos_respaldo
            WHERE user_id = :user_id AND usado = 0
            ORDER BY id
            """,
            user_id=user_id,
        )
        filas = cursor.fetchall()
        if not filas:
            return []
        columnas = [d[0].lower() for d in cursor.description]
        return [dict(zip(columnas, fila)) for fila in filas]


def marcar_codigo_respaldo_usado(codigo_id):
    with adquirir_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE codigos_respaldo SET usado = 1 WHERE id = :codigo_id",
            codigo_id=codigo_id,
        )


def actualizar_mfa(user_id, mfa_secret, mfa_activo):
    with adquirir_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            """
            UPDATE usuarios
            SET mfa_secret = :mfa_secret, mfa_activo = :mfa_activo
            WHERE id = :user_id
            """,
            mfa_secret=mfa_secret,
            mfa_activo=1 if mfa_activo else 0,
            user_id=uuid.UUID(user_id).bytes,
        )


def buscar_usuario_por_google_sub(google_sub):
    with adquirir_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            f"SELECT {_CAMPOS_USUARIO} FROM usuarios WHERE google_sub = :google_sub",
            google_sub=google_sub,
        )
        return _fila_a_usuario(cursor.fetchone(), cursor.description)


def vincular_google(user_id, google_sub):
    """Asocia una cuenta Google a un usuario existente y actualiza auth_provider."""
    with adquirir_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            """
            UPDATE usuarios
            SET google_sub = :google_sub, auth_provider = 'google'
            WHERE id = :user_id
            """,
            google_sub=google_sub,
            user_id=uuid.UUID(user_id).bytes,
        )


def crear_usuario_google(email, google_sub, nombre, apellido, password_hash):
    """Crea un usuario nuevo autenticado via Google (password_hash placeholder)."""
    nuevo_id = uuid.uuid4()
    with adquirir_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO usuarios
                (id, email, password_hash, nombre, apellido, rol, activo,
                 auth_provider, google_sub, creado_en)
            VALUES
                (:id, :email, :password_hash, :nombre, :apellido, :rol, 1,
                 'google', :google_sub, CURRENT_TIMESTAMP)
            """,
            id=nuevo_id.bytes,
            email=email,
            password_hash=password_hash,
            nombre=nombre,
            apellido=apellido,
            rol="cliente",
            google_sub=google_sub,
        )
    return {
        "id": str(nuevo_id),
        "email": email,
        "nombre": nombre,
        "apellido": apellido,
        "rol": "cliente",
    }