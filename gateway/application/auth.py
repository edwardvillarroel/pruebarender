import logging
from typing import Protocol

from gateway.domain.seguridad import (
    crear_hash,
    verificar_password,
    nuevo_jti,
    calcular_expiracion,
    esta_expirado,
    es_reuso,
    generar_codigo,
    generar_secreto_totp,
    construir_otpauth_uri,
    totp_qr_base64,
    verificar_totp,
    generar_codigos_respaldo,
    codigo_respaldo_a_hash,
    verificar_codigo_respaldo,
)
from gateway.infrastructure import repositorios
from gateway.infrastructure.correo import (
    ErrorEnvioCorreo,
    configurado_emailjs,
    enviar_correo_codigo,
    configurado_alerta_login,
    enviar_correo_alerta_login,
)

_log = logging.getLogger("gateway")

# En modo simulación (sin credenciales EMAILJS_*) el código se imprime en la
# consola del servidor para poder probar el flujo, pero NUNCA sale por la API
# ni llega al frontend.


class FabricaTokens(Protocol):
    def crear_par(self, *, user_id, rol, email, refresh_jti, refresh_expira) -> dict:
        ...

    def crear_ticket_mfa(self, *, user_id, rol, email) -> str:
        ...

    def decodificar_ticket(self, token: str) -> dict | None:
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


class CuentaBloqueada(Exception):
    """La cuenta está bloqueada temporalmente; `espera_seg` dice cuánto falta."""

    def __init__(self, espera_seg, *args):
        super().__init__(*args)
        self.espera_seg = espera_seg


class MfaRequerido(Exception):
    """El password es correcto pero falta el segundo factor."""

    def __init__(self, user, mfa_ticket, *args):
        super().__init__(*args)
        self.user = user
        self.mfa_ticket = mfa_ticket


class BloqueoMfa(Exception):
    """3 fallos MFA: bloqueo 15 min y hay que volver a pedir el password."""

    def __init__(self, espera_seg, *args):
        super().__init__(*args)
        self.espera_seg = espera_seg


DURACION_ACCESS_MINUTOS = 15
DURACION_REFRESH_MINUTOS = 7 * 24 * 60
DURACION_CODIGO_MINUTOS = 10
# Más corto que el de registro por seguridad: cambia credenciales de una cuenta existente.
DURACION_CODIGO_RECUPERACION_MINUTOS = 5

# --- Anti fuerza bruta ---
UMBRAL_FALLOS_PASSWORD = 5
UMBRAL_FALLOS_MFA = 3
DURACIONES_BLOQUEO_PASSWORD_MINUTOS = [15, 60, 1440]  # 15min -> 1h -> 24h
DURACION_BLOQUEO_MFA_MINUTOS = 15
CAPTCHA_DESDE_FALLOS = 3

MIN_PASSWORD = 8
MAX_PASSWORD = 72


def _usuario_a_publico(usuario: dict) -> dict:
    return {
        "id": usuario["id"],
        "email": usuario["email"],
        "nombre": usuario["nombre"],
        "apellido": usuario["apellido"],
        "rol": usuario["rol"],
        "foto": usuario.get("foto"),
        "mfa_activo": bool(usuario.get("mfa_activo")),
        "auth_provider": usuario.get("auth_provider", "local"),
    }


def _validar_password(password):
    if not password or len(password) < MIN_PASSWORD:
        raise DatosInvalidos(
            f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres"
        )
    if len(password) > MAX_PASSWORD:
        raise DatosInvalidos(
            f"La contraseña no puede superar los {MAX_PASSWORD} caracteres"
        )


def _validar_registro(email, password, nombre, apellido):
    email = (email or "").strip().lower()
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise DatosInvalidos("El correo electrónico no es válido")
    _validar_password(password)
    if not (nombre or "").strip():
        raise DatosInvalidos("El nombre es obligatorio")
    return email, (apellido or "").strip() or None, (nombre or "").strip()


# --------------------------------- anti fuerza bruta ---------------------------------

def _espera_activa(clave, tipo):
    """Segundos restantes de bloqueo para clave+tipo (0 si no está bloqueado)."""
    registro = repositorios.buscar_bloqueo(clave, tipo)
    if registro is None or registro.get("bloqueo_hasta") is None:
        return 0
    if esta_expirado(registro["bloqueo_hasta"]):
        return 0
    from gateway.domain.seguridad import a_utc
    restante = (a_utc(registro["bloqueo_hasta"]) - calcular_expiracion(0))
    return max(0, int(restante.total_seconds()))


def _registrar_fallo(clave, tipo, umbral, escalable=True):
    """Incrementa fallos de fuerte bruta y dispara el bloqueo si corresponde.

    Devuelve dict con: `espera_seg` (0 si no quedó bloqueado), `captcha_requerido`
    (a partir del 3er fallo) y `alerta` (True al alcanzar un umbral de bloqueo).

    Un bloqueo ya concedido se conserva hasta expirar: solo los múltiplos del
    umbral lo otorgan o renuevan. Los fallos intermedios no lo levantan.
    """
    registro = repositorios.buscar_bloqueo(clave, tipo)
    fallos = (registro or {}).get("fallos") or 0
    nivel = (registro or {}).get("nivel") or 0

    fallos += 1
    espera_seg = 0
    bloqueo_hasta = None

    if fallos % umbral == 0:
        nivel = max(nivel, fallos // umbral)
        duraciones = DURACIONES_BLOQUEO_PASSWORD_MINUTOS if escalable else [
            DURACION_BLOQUEO_MFA_MINUTOS
        ]
        indice = min(len(duraciones) - 1, nivel - 1)
        bloqueo_hasta = calcular_expiracion(duraciones[indice])
        espera_seg = duraciones[indice] * 60
    else:
        # Fallo que no es múltiplo del umbral: NO se anula un bloqueo vigente
        # (si se pisara con None, el bloqueo del 5º fallo duraría un solo
        # intento y quedarían 4 intentos sin restricción hasta el siguiente).
        # Solo se limpia si el bloqueo previo ya expiró.
        previo = (registro or {}).get("bloqueo_hasta")
        bloqueo_hasta = previo if previo and not esta_expirado(previo) else None

    repositorios.guardar_o_actualizar_bloqueo(
        clave, tipo, fallos, nivel, bloqueo_hasta
    )

    return {
        "espera_seg": espera_seg,
        "captcha_requerido": fallos >= CAPTCHA_DESDE_FALLOS,
        "alerta": fallos % umbral == 0,
    }


def _registrar_fallo_password(email):
    return _registrar_fallo(email, "password", UMBRAL_FALLOS_PASSWORD)


def _registrar_fallo_mfa(email):
    return _registrar_fallo(email, "mfa", UMBRAL_FALLOS_MFA, escalable=False)


def requiere_captcha_para_login(email):
    """True cuando la cuenta ya acumuló 3+ fallos y el próximo login exige captcha."""
    registro = repositorios.buscar_bloqueo((email or "").strip().lower(), "password")
    if registro is None:
        return False
    return (registro.get("fallos") or 0) >= CAPTCHA_DESDE_FALLOS


def _notificar_alerta_si_corresponde(email, resultado, ip):
    if not resultado.get("alerta"):
        return
    if not configurado_alerta_login():
        repositorios.registrar_log(
            "login_fail_alerta_pendiente", None, ip,
            "alerta no enviada: plantilla EMAILJS_TEMPLATE_ALERTA sin configurar",
        )
        return
    try:
        repositorios.registrar_log(
            "alerta_seguridad", None, ip,
            f"bloqueo por fallos en {email}",
        )
        enviar_correo_alerta_login(
            email,
            "Se detectaron varios intentos fallidos de acceso a tu cuenta. "
            "Si fuiste tú, ignora este correo. Si no, cambia tu contraseña.",
        )
    except ErrorEnvioCorreo:
        repositorios.registrar_log("alerta_seguridad_fallo", None, ip, email)


# --------------------------------- registro / recuperacion ---------------------------------

def despachar_codigo_verificacion(email, ip):
    """Genera y envía el código de confirmación de registro por correo.

    Con credenciales de EmailJS configuradas (`.env`) el envío es REAL y la
    función siempre devuelve None: el código nunca se expone en la respuesta.
    Sin credenciales queda en modo simulación: el código se imprime en la
    consola del gateway (solo servidor) para poder probar el flujo.
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

    if configurado_emailjs():
        try:
            enviar_correo_codigo(email, codigo)
        except ErrorEnvioCorreo:
            repositorios.registrar_log("codigo_correo_fallo", None, ip, email)
            raise CodigoNoEnviado()
    else:
        _log.warning(
            "MODO SIMULACIÓN: correo no configurado (EMAILJS_*). "
            "Código de verificación de registro para %s: %s",
            email,
            codigo,
        )

    repositorios.registrar_log("codigo_enviado", None, ip, email)
    return None


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

    Mismo contrato que el código de registro: con EmailJS el envío es real y el
    código no sale del servidor; sin credenciales se imprime en la consola del
    gateway (solo servidor). Devuelve (None, expira_en): la expiración viaja al
    frontend para el countdown (el código nunca).
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

    if configurado_emailjs():
        try:
            enviar_correo_codigo(email, codigo)
        except ErrorEnvioCorreo:
            repositorios.registrar_log("codigo_correo_fallo", None, ip, email)
            raise CodigoNoEnviado()
    else:
        _log.warning(
            "MODO SIMULACIÓN: correo no configurado (EMAILJS_*). "
            "Código de recuperación para %s: %s",
            email,
            codigo,
        )

    repositorios.registrar_log("codigo_recuperacion_enviado", None, ip, email)
    return None, expira_en


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
    _validar_password(nueva_password)

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


def cambiar_contrasena(user_id, password_actual, nueva_password, ip):
    """Cambio de contraseña con sesión activa; revoca TODAS las sesiones."""
    _validar_password(nueva_password)
    usuario = repositorios.buscar_usuario_por_id(user_id)
    if usuario is None or not usuario["activo"]:
        raise CredencialesInvalidas()

    if not verificar_password(password_actual or "", usuario["password_hash"]):
        repositorios.registrar_log("cambio_pass_fallo", user_id, ip, "password actual incorrecta")
        raise ContrasenaIncorrecta()
    if verificar_password(nueva_password, usuario["password_hash"]):
        raise DatosInvalidos("La nueva contraseña no puede ser igual a la anterior")

    repositorios.actualizar_password(user_id, crear_hash(nueva_password))
    repositorios.revocar_tokens_de_usuario(user_id)
    repositorios.registrar_log("cambio_pass_ok", user_id, ip, "")


# --------------------------------- login ---------------------------------

def _construir_sesion(usuario, ip, user_agent, fabrica_tokens):
    """Crea el par access/refresh y persiste el refresh. Asume password validado."""
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


def iniciar_sesion(email, password, ip, user_agent, fabrica_tokens):
    """Login email/password. Devuelve sesión completa o lanza MfaRequerido.

    Mensaje único `Credenciales incorrectas` (no revela si el correo existe).
    Con MFA activo, responde un ticket de 5 min para completar el 2do factor.
    """
    email = (email or "").strip().lower()

    espera = _espera_activa(email, "password")
    if espera > 0:
        repositorios.registrar_log("login_bloqueado", None, ip, email)
        raise CuentaBloqueada(espera)

    usuario = repositorios.buscar_usuario_por_email(email)
    uid = None if usuario is None else usuario["id"]

    if usuario is None or not usuario["activo"]:
        resultado = _registrar_fallo_password(email)
        _notificar_alerta_si_corresponde(email, resultado, ip)
        repositorios.registrar_log("login_fail", uid, ip, "email inexistente o inactivo")
        if resultado["espera_seg"]:
            repositorios.registrar_log("login_bloqueado", None, ip, email)
            raise CuentaBloqueada(resultado["espera_seg"])
        raise CredencialesInvalidas()

    if not verificar_password(password, usuario["password_hash"]):
        resultado = _registrar_fallo_password(email)
        _notificar_alerta_si_corresponde(email, resultado, ip)
        repositorios.registrar_log("login_fail", uid, ip, "password incorrecta")
        if resultado["espera_seg"]:
            repositorios.registrar_log("login_bloqueado", uid, ip, email)
            raise CuentaBloqueada(resultado["espera_seg"])
        raise CredencialesInvalidas()

    # Password correcto: limpiar contador de fallos.
    repositorios.limpiar_bloqueo(email, "password")

    if usuario.get("mfa_activo"):
        ticket = fabrica_tokens.crear_ticket_mfa(
            user_id=usuario["id"],
            rol=usuario["rol"],
            email=usuario["email"],
        )
        repositorios.registrar_log("mfa_pendiente", usuario["id"], ip, "")
        raise MfaRequerido(_usuario_a_publico(usuario), ticket)

    return _construir_sesion(usuario, ip, user_agent, fabrica_tokens)


def verificar_mfa(mfa_ticket, codigo, ip, user_agent, fabrica_tokens):
    """Completa el segundo factor: TOTP o código de respaldo.

    Devuelve la sesión completa. 3 fallos → BloqueoMfa (hay que reingresar password).
    """
    claims = fabrica_tokens.decodificar_ticket(mfa_ticket)
    if claims is None:
        raise CredencialesInvalidas()

    user_id = claims.get("sub")
    email = claims.get("email") or ""
    usuario = repositorios.buscar_usuario_por_id(user_id)
    if usuario is None or not usuario["activo"]:
        raise CredencialesInvalidas()

    espera = _espera_activa(email, "mfa")
    if espera > 0:
        raise BloqueoMfa(espera)

    codigo_valido = verificar_totp(
        usuario.get("mfa_secret"), (codigo or "").strip()
    )
    if codigo_valido:
        _mfa_exitoso(email)
        repositorios.registrar_log("mfa_ok", user_id, ip, "totp")
        return _construir_sesion(usuario, ip, user_agent, fabrica_tokens)

    # Segundo intento: código de respaldo (hasheado, de un solo uso).
    codigos = repositorios.buscar_codigo_respaldo_activo(user_id)
    for codigo_db in codigos:
        if verificar_codigo_respaldo(codigo, codigo_db["codigo_hash"]):
            repositorios.marcar_codigo_respaldo_usado(codigo_db["id"])
            _mfa_exitoso(email)
            repositorios.registrar_log("mfa_ok", user_id, ip, "codigo_respaldo")
            return _construir_sesion(usuario, ip, user_agent, fabrica_tokens)

    resultado = _registrar_fallo_mfa(email)
    repositorios.registrar_log("mfa_fail", user_id, ip, "totp/codigo invalido")
    if resultado["espera_seg"]:
        repositorios.registrar_log("mfa_bloqueado", user_id, ip, email)
        raise BloqueoMfa(resultado["espera_seg"])
    raise CredencialesInvalidas()


def _mfa_exitoso(email):
    repositorios.limpiar_bloqueo(email, "mfa")


# --------------------------------- MFA (gestion) ---------------------------------

def configurar_mfa(user_id):
    """Genera un secreto TOTP nuevo (aún NO activo) y lo guarda. Devuelve datos QR."""
    usuario = repositorios.buscar_usuario_por_id(user_id)
    if usuario is None:
        raise CredencialesInvalidas()

    secreto = generar_secreto_totp()
    repositorios.actualizar_mfa(user_id, secreto, False)
    repositorios.registrar_log("mfa_secreto_generado", user_id, "", "")
    return {
        "secreto": secreto,
        "otpauth_uri": construir_otpauth_uri(usuario["email"], secreto),
        "qr_base64": totp_qr_base64(usuario["email"], secreto),
    }


def activar_mfa(user_id, codigo):
    """Verifica el primer código TOTP, activa MFA y revoca TODAS las sesiones.

    Genera los 8 códigos de respaldo (hasheados) y los devuelve UNA sola vez.
    """
    usuario = repositorios.buscar_usuario_por_id(user_id)
    if usuario is None:
        raise CredencialesInvalidas()

    secreto = usuario.get("mfa_secret")
    if not secreto:
        raise DatosInvalidos("Primero genera el secreto con /auth/mfa/configurar")

    if not verificar_totp(secreto, (codigo or "").strip()):
        repositorios.registrar_log("mfa_activacion_fallo", user_id, "", "")
        raise CredencialesInvalidas()

    repositorios.actualizar_mfa(user_id, secreto, True)
    repositorios.revocar_tokens_de_usuario(user_id)
    codigos = generar_codigos_respaldo()
    repositorios.guardar_codigos_respaldo(
        user_id, [codigo_respaldo_a_hash(c) for c in codigos]
    )
    repositorios.registrar_log("mfa_activado", user_id, "", "sesiones revocadas")
    return {"codigos_respaldo": codigos}


def desactivar_mfa(user_id, password, codigo, ip):
    """Desactiva MFA pidiendo password actual + TOTP; revoca TODAS las sesiones."""
    usuario = repositorios.buscar_usuario_por_id(user_id)
    if usuario is None or not usuario["activo"]:
        raise CredencialesInvalidas()

    if not verificar_password(password or "", usuario["password_hash"]):
        repositorios.registrar_log("mfa_desactivacion_fallo", user_id, ip, "password incorrecta")
        raise ContrasenaIncorrecta()

    secreto = usuario.get("mfa_secret")
    if not secreto or not verificar_totp(secreto, (codigo or "").strip()):
        repositorios.registrar_log("mfa_desactivacion_fallo", user_id, ip, "totp invalido")
        raise CredencialesInvalidas()

    repositorios.actualizar_mfa(user_id, None, False)
    repositorios.guardar_codigos_respaldo(user_id, [])  # limpia códigos previos
    repositorios.revocar_tokens_de_usuario(user_id)
    repositorios.registrar_log("mfa_desactivado", user_id, ip, "sesiones revocadas")


def regenerar_codigos_respaldo(user_id):
    """Genera 8 códigos de respaldo nuevos (reemplaza los previos). Se muestran 1 vez."""
    usuario = repositorios.buscar_usuario_por_id(user_id)
    if usuario is None:
        raise CredencialesInvalidas()
    codigos = generar_codigos_respaldo()
    repositorios.guardar_codigos_respaldo(
        user_id, [codigo_respaldo_a_hash(c) for c in codigos]
    )
    repositorios.registrar_log("codigos_respaldo_generados", user_id, "", "")
    return {"codigos_respaldo": codigos}


# --------------------------------- login Google ---------------------------------

def _password_placeholder():
    """Hash de un valor aleatorio: el usuario de Google no puede loguear con password."""
    import secrets as _secrets
    return crear_hash(_secrets.token_urlsafe(32))


def iniciar_sesion_google(email, google_sub, nombre, apellido, ip, user_agent, fabrica_tokens):
    """Login/registro via Google. Crea, vincula o usa la cuenta y entrega sesión.

    Mismo contrato que `iniciar_sesion`: con MFA activo lanza MfaRequerido.
    Si el correo ya existe pero pertenece a una cuenta local, lo vincula (el
    correo verificado por Google demuestra titularidad).
    """
    email = (email or "").strip().lower()
    google_sub = (google_sub or "").strip()
    if not email or not google_sub:
        raise DatosInvalidos("Google no devolvió un perfil completo")

    usuario = repositorios.buscar_usuario_por_google_sub(google_sub)
    if usuario is None:
        existente = repositorios.buscar_usuario_por_email(email)
        if existente is not None:
            if not existente["activo"]:
                raise CredencialesInvalidas()
            if not existente.get("google_sub"):
                repositorios.vincular_google(existente["id"], google_sub)
            usuario = repositorios.buscar_usuario_por_google_sub(google_sub)
        else:
            creado = repositorios.crear_usuario_google(
                email=email,
                google_sub=google_sub,
                nombre=(nombre or "").strip() or email.split("@")[0],
                apellido=(apellido or "").strip(),
                password_hash=_password_placeholder(),
            )
            usuario = repositorios.buscar_usuario_por_id(creado["id"])
            repositorios.registrar_log("registro_google", creado["id"], ip, email)

    repositorios.limpiar_bloqueo(email, "password")

    if usuario.get("mfa_activo"):
        ticket = fabrica_tokens.crear_ticket_mfa(
            user_id=usuario["id"],
            rol=usuario["rol"],
            email=usuario["email"],
        )
        repositorios.registrar_log("mfa_pendiente", usuario["id"], ip, "google")
        raise MfaRequerido(_usuario_a_publico(usuario), ticket)

    return _construir_sesion(usuario, ip, user_agent, fabrica_tokens)


# --------------------------------- refresh / logout / perfil ---------------------------------

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