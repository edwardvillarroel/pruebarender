from typing import Protocol

from gateway.domain.seguridad import (
    crear_hash,
    verificar_password,
    nuevo_jti,
    calcular_expiracion,
    esta_expirado,
    es_reuso,
    generar_codigo,
)
from gateway.infrastructure import repositorios
from gateway.infrastructure.correo import (
    ErrorEnvioCorreo,
    configurado_emailjs,
    enviar_correo_codigo,
)


class FabricaTokens(Protocol):
    def crear_par(self, *, user_id, rol, email, refresh_jti, refresh_expira) -> dict:
        ...


class CredencialesInvalidas(Exception):
    pass


class CorreoIncorrecto(CredencialesInvalidas):
    pass


class ContrasenaIncorrecta(CredencialesInvalidas):
    pass


class ReusoDetectado(Exception):
    pass


class SesionExpirada(Exception):
    pass


class EmailRegistrado(Exception):
    pass


class DatosInvalidos(Exception):
    pass


class CodigoIncorrecto(Exception):
    pass


class CodigoExpirado(Exception):
    pass


class CodigoNoEnviado(Exception):
    pass


DURACION_ACCESS_MINUTOS = 15
DURACION_REFRESH_MINUTOS = 7 * 24 * 60
DURACION_CODIGO_MINUTOS = 10
# Más corto que el de registro por seguridad: cambia credenciales de una cuenta existente.
DURACION_CODIGO_RECUPERACION_MINUTOS = 5


def _usuario_a_publico(usuario: dict) -> dict:
    return {
        "id": usuario["id"],
        "email": usuario["email"],
        "nombre": usuario["nombre"],
        "apellido": usuario["apellido"],
        "rol": usuario["rol"],
        "foto": usuario.get("foto"),
    }


def _validar_registro(email, password, nombre, apellido):
    email = (email or "").strip().lower()
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise DatosInvalidos("El correo electrónico no es válido")
    if not password or len(password) < 6:
        raise DatosInvalidos("La contraseña debe tener al menos 6 caracteres")
    if not (nombre or "").strip():
        raise DatosInvalidos("El nombre es obligatorio")
    return email, (apellido or "").strip() or None, (nombre or "").strip()


def registrar_usuario(email, password, nombre, apellido, telefono, ip, user_agent, fabrica_tokens):
    """Registra un usuario con rol fijo `cliente` y lo deja con sesión iniciada.

    El rol nunca se recibe del cliente: el registro público jamás crea admins.
    """
    email, apellido, nombre = _validar_registro(email, password, nombre, apellido)

    if repositorios.buscar_usuario_por_email(email) is not None:
        raise EmailRegistrado()

    password_hash = crear_hash(password)
    usuario = repositorios.crear_usuario(
        email=email,
        password_hash=password_hash,
        nombre=nombre,
        apellido=apellido,
        telefono=(telefono or "").strip() or None,
        rol="cliente",
    )
    repositorios.registrar_log("registro_ok", usuario["id"], ip, email)
    return iniciar_sesion(email, password, ip, user_agent, fabrica_tokens)


def despachar_codigo_verificacion(email, ip):
    """Genera y envía el código de confirmación de registro por correo.

    Con credenciales de EmailJS configuradas (`.env`) el envío es REAL y la
    función devuelve None: el código NUNCA se expone en la respuesta.
    Sin credenciales queda en MOCK: devuelve el código para poder probar.
    """
    email = (email or "").strip().lower()
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise DatosInvalidos("El correo electrónico no es válido")
    if repositorios.buscar_usuario_por_email(email) is not None:
        raise EmailRegistrado()

    codigo = generar_codigo()
    repositorios.guardar_codigo(
        email=email,
        codigo_hash=crear_hash(codigo),
        expira_en=calcular_expiracion(DURACION_CODIGO_MINUTOS),
    )

    con_correo = configurado_emailjs()
    if con_correo:
        try:
            enviar_correo_codigo(email, codigo)
        except ErrorEnvioCorreo:
            repositorios.registrar_log("codigo_correo_fallo", None, ip, email)
            raise CodigoNoEnviado()

    repositorios.registrar_log("codigo_enviado", None, ip, email)
    return None if con_correo else codigo


def confirmar_registro(email, codigo, password, nombre, apellido, telefono, ip, user_agent, fabrica_tokens):
    """Valida el código de verificación y crea el usuario con sesión iniciada."""
    email, apellido, nombre = _validar_registro(email, password, nombre, apellido)

    pendiente = repositorios.buscar_codigo(email)
    if pendiente is None or not verificar_password((codigo or "").strip(), pendiente["codigo_hash"]):
        repositorios.registrar_log("codigo_invalido", None, ip, email)
        raise CodigoIncorrecto()
    if esta_expirado(pendiente["expira_en"]):
        repositorios.registrar_log("codigo_expirado", None, ip, email)
        raise CodigoExpirado()
    if repositorios.buscar_usuario_por_email(email) is not None:
        raise EmailRegistrado()

    repositorios.marcar_codigo_usado(email)
    password_hash = crear_hash(password)
    usuario = repositorios.crear_usuario(
        email=email,
        password_hash=password_hash,
        nombre=nombre,
        apellido=apellido,
        telefono=(telefono or "").strip() or None,
        rol="cliente",
    )
    repositorios.registrar_log("registro_ok", usuario["id"], ip, email)
    return iniciar_sesion(email, password, ip, user_agent, fabrica_tokens)


def despachar_codigo_recuperacion(email, ip):
    """Genera y envía el código para restablecer la contraseña de una cuenta EXISTENTE.

    Mismo contrato mock→real que el código de registro: con EmailJS el envío es real
    y devuelve None; sin credenciales devuelve el código para poder probar.
    Devuelve (codigo, expira_en): la expiración viaja al frontend para el countdown.
    """
    email = (email or "").strip().lower()
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise DatosInvalidos("El correo electrónico no es válido")
    if repositorios.buscar_usuario_por_email(email) is None:
        raise DatosInvalidos("No existe una cuenta con ese correo electrónico")

    codigo = generar_codigo()
    expira_en = calcular_expiracion(DURACION_CODIGO_RECUPERACION_MINUTOS)
    repositorios.guardar_codigo(
        email=email,
        codigo_hash=crear_hash(codigo),
        expira_en=expira_en,
    )

    con_correo = configurado_emailjs()
    if con_correo:
        try:
            enviar_correo_codigo(email, codigo)
        except ErrorEnvioCorreo:
            repositorios.registrar_log("codigo_correo_fallo", None, ip, email)
            raise CodigoNoEnviado()

    repositorios.registrar_log("codigo_recuperacion_enviado", None, ip, email)
    return (None if con_correo else codigo), expira_en


def validar_codigo_recuperacion(email, codigo):
    """Valida un código de recuperación SIN consumirlo ni cambiar nada.

    Permite al frontend confirmar el código antes de mostrar los campos de la
    nueva contraseña; `restablecer_contrasena` vuelve a validarlo al confirmar.
    """
    email = (email or "").strip().lower()
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise DatosInvalidos("El correo electrónico no es válido")
    pendiente = repositorios.buscar_codigo(email)
    if pendiente is None or not verificar_password((codigo or "").strip(), pendiente["codigo_hash"]):
        raise CodigoIncorrecto()
    if esta_expirado(pendiente["expira_en"]):
        raise CodigoExpirado()


def restablecer_contrasena(email, codigo, nueva_password, ip):
    """Valida el código de recuperación y cambia la contraseña del usuario.

    Revoca los refresh tokens del usuario para forzar un nuevo inicio de sesión.
    """
    email = (email or "").strip().lower()
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise DatosInvalidos("El correo electrónico no es válido")
    if not nueva_password or len(nueva_password) < 6:
        raise DatosInvalidos("La contraseña debe tener al menos 6 caracteres")

    usuario = repositorios.buscar_usuario_por_email(email)
    if usuario is None or not usuario["activo"]:
        raise DatosInvalidos("No existe una cuenta con ese correo electrónico")

    pendiente = repositorios.buscar_codigo(email)
    if pendiente is None or not verificar_password((codigo or "").strip(), pendiente["codigo_hash"]):
        repositorios.registrar_log("codigo_invalido", usuario["id"], ip, email)
        raise CodigoIncorrecto()
    if esta_expirado(pendiente["expira_en"]):
        repositorios.registrar_log("codigo_expirado", usuario["id"], ip, email)
        raise CodigoExpirado()

    if verificar_password(nueva_password, usuario["password_hash"]):
        raise DatosInvalidos("La nueva contraseña no puede ser igual a la anterior")

    repositorios.marcar_codigo_usado(email)
    repositorios.actualizar_password(usuario["id"], crear_hash(nueva_password))
    repositorios.revocar_tokens_de_usuario(usuario["id"])
    repositorios.registrar_log("password_reset", usuario["id"], ip, email)


def iniciar_sesion(email, password, ip, user_agent, fabrica_tokens):
    usuario = repositorios.buscar_usuario_por_email(email)
    uid = None if usuario is None else usuario["id"]

    if usuario is None or not usuario["activo"]:
        repositorios.registrar_log("login_fail", uid, ip, "email inexistente o inactivo")
        raise CorreoIncorrecto()

    if not verificar_password(password, usuario["password_hash"]):
        repositorios.registrar_log("login_fail", uid, ip, "password incorrecta")
        raise ContrasenaIncorrecta()

    jti = nuevo_jti()
    expira_en = calcular_expiracion(DURACION_REFRESH_MINUTOS)
    tokens = fabrica_tokens.crear_par(
        user_id=usuario["id"],
        rol=usuario["rol"],
        email=usuario["email"],
        refresh_jti=jti,
        refresh_expira=expira_en,
    )
    repositorios.guardar_refresh(jti, usuario["id"], expira_en, ip, user_agent)
    repositorios.registrar_log("login_ok", usuario["id"], ip, "")
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "user": _usuario_a_publico(usuario),
    }


def rotar_refresh(jti, ip, fabrica_tokens):
    registro = repositorios.buscar_refresh(jti)
    if registro is None:
        raise CredencialesInvalidas()

    if es_reuso(registro):
        user_id = registro["user_id"]
        repositorios.revocar_tokens_de_usuario(user_id)
        repositorios.registrar_log(
            "reuso", user_id, ip, "refresh revocado usado -> se revoca toda la sesion"
        )
        raise ReusoDetectado(user_id)

    if esta_expirado(registro["expira_en"]):
        repositorios.registrar_log("refresh_expirado", registro["user_id"], ip, "")
        raise SesionExpirada()

    usuario = repositorios.buscar_usuario_por_id(registro["user_id"])
    if usuario is None:
        raise CredencialesInvalidas()

    repositorios.revocar_refresh(jti)

    nuevo_jti_valor = nuevo_jti()
    expira_en = calcular_expiracion(DURACION_REFRESH_MINUTOS)
    tokens = fabrica_tokens.crear_par(
        user_id=usuario["id"],
        rol=usuario["rol"],
        email=usuario["email"],
        refresh_jti=nuevo_jti_valor,
        refresh_expira=expira_en,
    )
    repositorios.guardar_refresh(nuevo_jti_valor, usuario["id"], expira_en, ip, "rotacion")
    repositorios.registrar_log("refresh_ok", usuario["id"], ip, "token rotado")
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "user": _usuario_a_publico(usuario),
    }


def cerrar_sesion(jti, ip):
    if jti is None:
        return
    registro = repositorios.buscar_refresh(jti)
    if registro is not None:
        repositorios.revocar_refresh(jti)
        repositorios.registrar_log("logout", registro["user_id"], ip, "")


def obtener_perfil(user_id):
    usuario = repositorios.buscar_usuario_por_id(user_id)
    if usuario is None:
        raise CredencialesInvalidas()
    return _usuario_a_publico(usuario)