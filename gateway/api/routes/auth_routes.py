from flask import Blueprint, current_app, jsonify, make_response, request
from flask_jwt_extended import decode_token, get_jwt_identity, jwt_required
from gateway.api.rate_limit import limiter
from gateway.application.auth import (
    CodigoExpirado,
    CodigoIncorrecto,
    CodigoNoEnviado,
    ContrasenaIncorrecta,
    CorreoIncorrecto,
    CredencialesInvalidas,
    DatosInvalidos,
    EmailRegistrado,
    ReusoDetectado,
    SesionExpirada,
    cerrar_sesion,
    confirmar_registro,
    despachar_codigo_recuperacion,
    despachar_codigo_verificacion,
    iniciar_sesion,
    obtener_perfil,
    restablecer_contrasena,
    rotar_refresh,
    validar_codigo_recuperacion,
)
from gateway.infrastructure.token_service import TokenServiceFlaskJWT

auth_bp = Blueprint("auth", __name__)
servicio_tokens = TokenServiceFlaskJWT()

COOKIE_REFRESH = "refresh_token"

def _ip_cliente():
    return request.remote_addr or "0.0.0.0"

def _user_agent():
    return (request.headers.get("User-Agent") or "")[:255]

def _responder_con_sesion(cuerpo, sesion):
    respuesta = make_response(jsonify(**cuerpo))
    respuesta.set_cookie(
        COOKIE_REFRESH,
        value=sesion["refresh_token"],
        httponly=True,
        secure=current_app.config.get("COOKIE_SECURE", True),
        samesite="Strict",
        path="/api/auth"
    )
    return respuesta

def _borrar_cookie_refresh(respuesta):
    respuesta.delete_cookie(
        COOKIE_REFRESH,
        path="/api/auth",
        secure=current_app.config.get("COOKIE_SECURE", True),
        samesite="Strict",
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


@auth_bp.post("/auth/login")
@limiter.limit("5 per minute")
def login():
    datos = request.get_json(silent=True) or {}
    email = (datos.get("email") or datos.get("username") or "").strip().lower()
    password = datos.get("password", "")
    if not email or not password:
        return jsonify(mensaje="Correo y contraseña son obligatorios"), 400
    try:
        sesion = iniciar_sesion(email, password, _ip_cliente(), _user_agent(), servicio_tokens)
    except CorreoIncorrecto:
        return jsonify(mensaje="Correo incorrecto"), 401
    except ContrasenaIncorrecta:
        return jsonify(mensaje="Contraseña incorrecta"), 401
    except CredencialesInvalidas:
        return jsonify(mensaje="Credenciales invalidas"), 401
    return _responder_con_sesion(
        {"access_token": sesion["access_token"], "user": sesion["user"]}, sesion
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
    # El código NO se devuelve ni se muestra: viaja solo por correo (o a la
    # consola del servidor en modo simulación).
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
    except DatosInvalidos as e:
        return jsonify(mensaje=str(e)), 400
    except CodigoNoEnviado:
        return jsonify(mensaje="No se pudo enviar el correo de verificación. Intenta de nuevo"), 502
    # El código NO se devuelve ni se muestra: viaja solo por correo (o a la
    # consola del servidor en modo simulación). `expira_en` va al countdown.
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
    except DatosInvalidos as e:
        return jsonify(mensaje=str(e)), 400
    except CodigoIncorrecto:
        return jsonify(mensaje="El código de verificación es incorrecto"), 400
    except CodigoExpirado:
        return jsonify(mensaje="El código de verificación expiró. Solicita uno nuevo"), 400
    return jsonify(mensaje="Contraseña actualizada. Ya puedes iniciar sesión")


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