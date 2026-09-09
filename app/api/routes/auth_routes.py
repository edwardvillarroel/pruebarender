from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt, jwt_required

from app.application.auth.autenticar import (
    CredencialesInvalidas,
    autenticar_admin,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/auth/register")
def registrar():
    # TODO: validar email/contraseña, hashear con bcrypt, persistir usuario.
    # Temporal: solo existe el administrador (ver admin en autenticar.py).
    raise NotImplementedError


@auth_bp.post("/auth/login")
def iniciar_sesion():
    datos = request.get_json(silent=True) or {}
    username = datos.get("username") or datos.get("email")
    password = datos.get("password", "")

    if not username or not password:
        return jsonify(mensaje="Correo y contraseña son obligatorios"), 400

    try:
        sesion = autenticar_admin(username.strip(), password)
    except CredencialesInvalidas:
        return jsonify(mensaje="Credenciales inválidas"), 401

    access_token = create_access_token(
        identity=sesion.username,
        additional_claims={"rol": sesion.rol, "username": sesion.username},
    )
    return jsonify(
        access_token=access_token,
        user={"username": sesion.username, "rol": sesion.rol},
    )


@auth_bp.get("/auth/me")
@jwt_required()
def perfil():
    claims = get_jwt()
    return jsonify(
        user={
            "username": claims.get("username"),
            "rol": claims.get("rol"),
        }
    )