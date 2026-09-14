from flask import Blueprint, current_app, jsonify, make_response, request
from flask_jwt_extended import decode_token, get_jwt_identity, jwt_required
from gateway.api.rate_limit import limiter
from gateway.application.auth import (
    CredencialesInvalidas, 
    ReusoDetectado,
    SesionExpirada,
    cerrar_sesion,
    iniciar_sesion,
    obtener_perfil,
    rotar_refresh,
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
    except CredencialesInvalidas:
        return jsonify(mensaje="Credenciales invalidas"), 401
    return _responder_con_sesion(
        {"access_token": sesion["access_token"], "user": sesion["user"]}, sesion
    )

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