import bcrypt
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt, jwt_required

from app.infrastructure.database.models.usuario_model import UsuarioModel

auth_bp = Blueprint("auth", __name__)


def _usuario_a_publico(usuario: UsuarioModel) -> dict:
    return {
        "id": str(usuario.id),
        "email": usuario.email,
        "nombre": usuario.nombre,
        "apellido": usuario.apellido,
        "rol": usuario.rol,
    }


@auth_bp.post("/auth/register")
def registrar():
    # TODO: validar email/contraseña, hashear con bcrypt, persistir usuario.
    raise NotImplementedError


@auth_bp.post("/auth/login")
def iniciar_sesion():
    datos = request.get_json(silent=True) or {}
    email = datos.get("email") or datos.get("username")
    password = datos.get("password", "")

    if not email or not password:
        return jsonify(mensaje="Correo y contraseña son obligatorios"), 400

    usuario = UsuarioModel.query.filter_by(email=email.strip().lower()).first()
    if usuario is None or not usuario.activo:
        return jsonify(mensaje="Credenciales inválidas"), 401

    try:
        hash_valido = bcrypt.checkpw(
            password.encode("utf-8"), usuario.password_hash.encode("utf-8")
        )
    except ValueError:
        hash_valido = False
    if not hash_valido:
        return jsonify(mensaje="Credenciales inválidas"), 401

    access_token = create_access_token(
        identity=str(usuario.id),
        additional_claims={"rol": usuario.rol, "email": usuario.email},
    )
    return jsonify(
        access_token=access_token,
        user=_usuario_a_publico(usuario),
    )


@auth_bp.get("/auth/me")
@jwt_required()
def perfil():
    claims = get_jwt()
    usuario = UsuarioModel.query.get(claims.get("sub"))
    if usuario is None:
        return jsonify(mensaje="Usuario no encontrado"), 404
    return jsonify(user=_usuario_a_publico(usuario))