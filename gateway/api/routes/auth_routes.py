from urllib.parse import urlencode

from flask import Blueprint, current_app, jsonify, make_response, redirect, request
from flask_jwt_extended import decode_token, get_jwt_identity, jwt_required
from gateway.api.rate_limit import limiter
from gateway.application.auth import (
    BloqueoMfa,
    CodigoExpirado,
    CodigoIncorrecto,
    CodigoNoEnviado,
    ContrasenaIncorrecta,
    CorreoIncorrecto,
    CredencialesInvalidas,
    CuentaBloqueada,
    CuentaSoloGoogle,
    DatosInvalidos,
    EmailRegistrado,
    MfaRequerido,
    ReusoDetectado,
    SesionExpirada,
    activar_mfa,
    cambiar_contrasena,
    cerrar_sesion,
    configurar_mfa,
    confirmar_registro,
    desactivar_mfa,
    despachar_codigo_recuperacion,
    despachar_codigo_verificacion,
    iniciar_sesion,
    iniciar_sesion_google,
    obtener_perfil,
    regenerar_codigos_respaldo,
    requiere_captcha_para_login,
    restablecer_contrasena,
    rotar_refresh,
    validar_codigo_recuperacion,
    verificar_mfa,
)
from gateway.infrastructure import google_oauth, recaptcha
from gateway.infrastructure.token_service import TokenServiceFlaskJWT

auth_bp = Blueprint("auth", __name__)
servicio_tokens = TokenServiceFlaskJWT()

COOKIE_REFRESH = "refresh_token"
_FRONTEND_URL = "http://localhost:5173"


def _frontend():
    url = current_app.config.get("FRONTEND_URL") or _FRONTEND_URL
    return url.rstrip("/")


def _redirigir_al_front(**parametros):

    return redirect(f"{_frontend()}?{urlencode(parametros)}")


def _ip_cliente():
    reenviada = request.headers.get("X-Forwarded-For", "")
    if reenviada:
        ultima = reenviada.split(",")[-1].strip()
        if ultima:
            return ultima[:45]
    return request.remote_addr or "0.0.0.0"


def _user_agent():
    return (request.headers.get("User-Agent") or "")[:255]


def _samesite_cookie():
    return current_app.config.get("COOKIE_SAMESITE", "Strict")


def _aplicar_cookie_refresh(respuesta, refresh_token):

    respuesta.set_cookie(
        COOKIE_REFRESH,
        value=refresh_token,
        httponly=True,
        secure=current_app.config.get("COOKIE_SECURE", True),
        samesite=_samesite_cookie(),
        path="/api/auth",
    )
    return respuesta


def _responder_con_sesion(cuerpo, sesion):
    return _aplicar_cookie_refresh(
        make_response(jsonify(**cuerpo)), sesion["refresh_token"]
    )


def _borrar_cookie_refresh(respuesta):
    respuesta.delete_cookie(
        COOKIE_REFRESH,
        path="/api/auth",
        secure=current_app.config.get("COOKIE_SECURE", True),
        samesite=_samesite_cookie(),
        httponly=True,
    )
    return respuesta


COOKIE_MFA = "mfa_ticket"


def _sete_cookie_mfa(respuesta, ticket):
    respuesta.set_cookie(
        COOKIE_MFA,
        value=ticket,
        httponly=True,
        secure=current_app.config.get("COOKIE_SECURE", True),
        samesite=_samesite_cookie(),
        path="/api/auth",
        max_age=300,
    )
    return respuesta


def _borrar_cookie_mfa(respuesta):
    respuesta.delete_cookie(
        COOKIE_MFA,
        path="/api/auth",
        secure=current_app.config.get("COOKIE_SECURE", True),
        samesite=_samesite_cookie(),
        httponly=True,
    )
    return respuesta


def _jti_del_cookie():
    token = request.cookies.get(COOKIE_REFRESH)
    if not token:
        return None
    try:
        return decode_token(token).get("jti")
    except Exception:
        return None


def _captcha_valido(datos):
    token = datos.get("captcha_token") or ""
    return recaptcha.verificar_token(token)


def _mfa_ticket_del_cookie_o_body(datos):
    ticket = (datos or {}).get("mfa_ticket") or request.cookies.get("mfa_ticket")
    return ticket or ""


@auth_bp.post("/auth/login")
@limiter.limit("20 per minute")
def login():
    datos = request.get_json(silent=True) or {}
    email = (datos.get("email") or datos.get("username") or "").strip().lower()
    password = datos.get("password", "")
    if not email or not password:
        return jsonify(mensaje="Correo y contraseña son obligatorios"), 400

    if requiere_captcha_para_login(email) and not _captcha_valido(datos):
        return jsonify(
            mensaje="Credenciales incorrectas", captcha_requerido=True
        ), 401

    try:
        sesion = iniciar_sesion(email, password, _ip_cliente(), _user_agent(), servicio_tokens)
    except CuentaBloqueada as e:
        return jsonify(
            mensaje="Demasiados intentos. Vuelve a intentarlo más tarde",
            espera_seg=e.espera_seg,
        ), 429
    except MfaRequerido as e:
        return jsonify(
            mensaje="Código de verificación requerido",
            mfa_requerido=True,
            mfa_ticket=e.mfa_ticket,
            user=e.user,
        )
    except (CorreoIncorrecto, ContrasenaIncorrecta, CredencialesInvalidas):
        return jsonify(
            mensaje="Credenciales incorrectas",
            captcha_requerido=requiere_captcha_para_login(email),
        ), 401
    return _responder_con_sesion(
        {"access_token": sesion["access_token"], "user": sesion["user"]}, sesion
    )


@auth_bp.post("/auth/mfa/verificar")
@limiter.limit("5 per minute")
def mfa_verificar():
    datos = request.get_json(silent=True) or {}
    try:
        sesion = verificar_mfa(
            _mfa_ticket_del_cookie_o_body(datos),
            datos.get("codigo", ""),
            _ip_cliente(),
            _user_agent(),
            servicio_tokens,
        )
    except CredencialesInvalidas:
        respuesta = _borrar_cookie_refresh(
            _borrar_cookie_mfa(jsonify(mensaje="Código de verificación incorrecto o expirado"))
        )
        return respuesta, 401
    except BloqueoMfa as e:
        respuesta = _borrar_cookie_mfa(
            jsonify(
                mensaje="Demasiados intentos. Vuelve a iniciar sesión",
                espera_seg=e.espera_seg,
                mfa_requerido=False,
            )
        )
        return respuesta, 429
    respuesta = _responder_con_sesion(
        {"access_token": sesion["access_token"], "user": sesion["user"]}, sesion
    )
    return _borrar_cookie_mfa(respuesta)


@auth_bp.get("/auth/mfa/configurar")
@jwt_required()
def mfa_configurar():
    try:
        datos = configurar_mfa(get_jwt_identity())
    except CredencialesInvalidas:
        return jsonify(mensaje="Usuario no encontrado"), 404
    except CuentaSoloGoogle as e:
        return jsonify(mensaje=str(e)), 409
    return jsonify(**datos)


@auth_bp.post("/auth/mfa/activar")
@jwt_required()
def mfa_activar():
    datos = request.get_json(silent=True) or {}
    try:
        resultado = activar_mfa(get_jwt_identity(), datos.get("codigo", ""))
    except CuentaSoloGoogle as e:
        return jsonify(mensaje=str(e)), 409
    except DatosInvalidos as e:
        return jsonify(mensaje=str(e)), 400
    except CredencialesInvalidas:
        return jsonify(mensaje="Código incorrecto"), 400
    cuerpo = {
        "mensaje": "MFA activado. Guarda tus códigos de respaldo.",
        "codigos_respaldo": resultado["codigos_respaldo"],
    }
    respuesta = _borrar_cookie_refresh(jsonify(**cuerpo))
    return respuesta


@auth_bp.post("/auth/mfa/desactivar")
@jwt_required()
def mfa_desactivar():
    datos = request.get_json(silent=True) or {}
    try:
        desactivar_mfa(
            get_jwt_identity(),
            datos.get("password", ""),
            datos.get("codigo", ""),
            _ip_cliente(),
        )
    except ContrasenaIncorrecta:
        return jsonify(mensaje="Contraseña incorrecta"), 401
    except CredencialesInvalidas:
        return jsonify(mensaje="Código incorrecto"), 400
    respuesta = _borrar_cookie_refresh(
        jsonify(mensaje="MFA desactivado. Se cerraron todas las sesiones.")
    )
    return respuesta


@auth_bp.post("/auth/mfa/codigos-respaldo")
@jwt_required()
def mfa_codigos_respaldo():
    try:
        resultado = regenerar_codigos_respaldo(get_jwt_identity())
    except CredencialesInvalidas:
        return jsonify(mensaje="Usuario no encontrado"), 404
    return jsonify(
        mensaje="Nuevos códigos generados. Los anteriores ya no sirven.",
        **resultado,
    )


@auth_bp.post("/auth/registro/crear-codigo")
@limiter.limit("5 per minute")
def crear_codigo_verificacion():
    datos = request.get_json(silent=True) or {}
    email = datos.get("email", "")
    try:
        despachar_codigo_verificacion(email, _ip_cliente())
    except DatosInvalidos as e:
        return jsonify(mensaje=str(e)), 400
    except EmailRegistrado:
        return jsonify(mensaje="Ya existe una cuenta con ese correo electrónico"), 409
    except CodigoNoEnviado:
        return jsonify(mensaje="No se pudo enviar el correo de verificación. Intenta de nuevo"), 502
    return jsonify(mensaje="Código de verificación enviado a tu correo")


@auth_bp.post("/auth/registro/confirmar")
@limiter.limit("5 per minute")
def confirmar_cuenta():
    datos = request.get_json(silent=True) or {}
    try:
        sesion = confirmar_registro(
            email=datos.get("email", ""),
            codigo=datos.get("codigo", ""),
            password=datos.get("password", ""),
            nombre=datos.get("nombre", ""),
            apellido=datos.get("apellido", ""),
            telefono=datos.get("telefono"),
            ip=_ip_cliente(),
            user_agent=_user_agent(),
            fabrica_tokens=servicio_tokens,
        )
    except DatosInvalidos as e:
        return jsonify(mensaje=str(e)), 400
    except CodigoIncorrecto:
        return jsonify(mensaje="El código de verificación es incorrecto"), 400
    except CodigoExpirado:
        return jsonify(mensaje="El código de verificación expiró. Solicita uno nuevo"), 400
    except EmailRegistrado:
        return jsonify(mensaje="Ya existe una cuenta con ese correo electrónico"), 409
    return _responder_con_sesion(
        {"access_token": sesion["access_token"], "user": sesion["user"]}, sesion
    )


@auth_bp.post("/auth/recuperar/crear-codigo")
@limiter.limit("5 per minute")
def crear_codigo_recuperacion():
    datos = request.get_json(silent=True) or {}
    email = datos.get("email", "")
    try:
        _, expira_en = despachar_codigo_recuperacion(email, _ip_cliente())
    except CuentaSoloGoogle as e:
        return jsonify(mensaje=str(e)), 409
    except DatosInvalidos as e:
        return jsonify(mensaje=str(e)), 400
    except CodigoNoEnviado:
        return jsonify(mensaje="No se pudo enviar el correo de verificación. Intenta de nuevo"), 502
    return jsonify(mensaje="Código de recuperación enviado a tu correo", expira_en=expira_en.isoformat())


@auth_bp.post("/auth/recuperar/verificar-codigo")
@limiter.limit("5 per minute")
def verificar_codigo_recuperacion():
    datos = request.get_json(silent=True) or {}
    try:
        validar_codigo_recuperacion(
            email=datos.get("email", ""),
            codigo=datos.get("codigo", ""),
        )
    except DatosInvalidos as e:
        return jsonify(mensaje=str(e)), 400
    except CodigoIncorrecto:
        return jsonify(mensaje="El código de verificación es incorrecto"), 400
    except CodigoExpirado:
        return jsonify(mensaje="El código de verificación expiró. Solicita uno nuevo"), 400
    return jsonify(mensaje="Código válido")


@auth_bp.post("/auth/recuperar/confirmar")
@limiter.limit("5 per minute")
def confirmar_recuperacion():
    datos = request.get_json(silent=True) or {}
    try:
        restablecer_contrasena(
            email=datos.get("email", ""),
            codigo=datos.get("codigo", ""),
            nueva_password=datos.get("password", ""),
            ip=_ip_cliente(),
        )
    except CuentaSoloGoogle as e:
        return jsonify(mensaje=str(e)), 409
    except DatosInvalidos as e:
        return jsonify(mensaje=str(e)), 400
    except CodigoIncorrecto:
        return jsonify(mensaje="El código de verificación es incorrecto"), 400
    except CodigoExpirado:
        return jsonify(mensaje="El código de verificación expiró. Solicita uno nuevo"), 400
    return jsonify(mensaje="Contraseña actualizada. Ya puedes iniciar sesión")


@auth_bp.post("/auth/cambiar-contrasena")
@jwt_required()
@limiter.limit("5 per minute")
def cambiar_contrasena_ruta():
    datos = request.get_json(silent=True) or {}
    try:
        cambiar_contrasena(
            get_jwt_identity(),
            datos.get("password_actual", ""),
            datos.get("nueva_password", ""),
            _ip_cliente(),
        )
    except CuentaSoloGoogle as e:
        return jsonify(mensaje=str(e)), 409
    except DatosInvalidos as e:
        return jsonify(mensaje=str(e)), 400
    except (ContrasenaIncorrecta, CredencialesInvalidas):
        return jsonify(mensaje="Contraseña actual incorrecta"), 401
    respuesta = _borrar_cookie_refresh(
        jsonify(mensaje="Contraseña actualizada. Se cerraron todas las sesiones.")
    )
    return respuesta


@auth_bp.post("/auth/refresh")
@limiter.limit("10 per minute")
def refrescar():
    jti = _jti_del_cookie()
    if jti is None:
        return jsonify(mensaje="No hay sesión activa"), 401
    try:
        sesion = rotar_refresh(jti, _ip_cliente(), servicio_tokens)
    except ReusoDetectado:
        respuesta = _borrar_cookie_refresh(
            jsonify(mensaje="Sesión comprometida. Vuelva a ingresar.")
        )
        return respuesta, 401
    except (SesionExpirada, CredencialesInvalidas):
        respuesta = _borrar_cookie_refresh(jsonify(mensaje="Sesión expirada"))
        return respuesta, 401
    return _responder_con_sesion(
        {"access_token": sesion["access_token"], "user": sesion["user"]}, sesion
    )


@auth_bp.post("/auth/logout")
def logout():
    jti = _jti_del_cookie()
    if jti is not None:
        cerrar_sesion(jti, _ip_cliente())
    return _borrar_cookie_refresh(jsonify(mensaje="Sesion Cerrada"))

@auth_bp.get("/auth/me")
@jwt_required()
def perfil():
    try:
        user = obtener_perfil(get_jwt_identity())
    except CredencialesInvalidas:
        return jsonify(mensaje="Usuario no encontrado"), 404
    return jsonify(user=user)



@auth_bp.get("/auth/google/url")
@limiter.limit("10 per minute")
def google_url():
    try:
        url = google_oauth.generar_url_autorizacion()
    except google_oauth.GoogleOAuthError as error:
        return jsonify(mensaje=str(error)), 503
    return jsonify(url=url)


@auth_bp.get("/auth/google/callback")
def google_callback():

    code = request.args.get("code", "")
    state = request.args.get("state", "")
    try:
        perfil = google_oauth.intercambiar_codigo(code, state)
    except google_oauth.GoogleOAuthError as error:
        return _redirigir_al_front(login="google", error=str(error))
    except CredencialesInvalidas:
        return _redirigir_al_front(login="google", error="cuenta_inactiva")

    try:
        sesion = iniciar_sesion_google(
            email=perfil["email"],
            google_sub=perfil["sub"],
            nombre=perfil["nombre"],
            apellido=perfil["apellido"],
            ip=_ip_cliente(),
            user_agent=_user_agent(),
            fabrica_tokens=servicio_tokens,
        )
    except MfaRequerido as e:
        respuesta = _redirigir_al_front(login="google", mfa=1)
        return _sete_cookie_mfa(respuesta, e.mfa_ticket)
    except (DatosInvalidos, CredencialesInvalidas) as e:
        detalle = getattr(e, "espera_seg", None)
        mensaje = "cuenta_inactiva" if isinstance(e, CredencialesInvalidas) else str(e)
        return _redirigir_al_front(login="google", error=mensaje)

    respuesta = _redirigir_al_front(login="google")
    return _aplicar_cookie_refresh(respuesta, sesion["refresh_token"])