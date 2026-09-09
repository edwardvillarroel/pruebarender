from flask import Blueprint, jsonify
from flask_jwt_extended import create_access_token, jwt_required

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/auth/register")
def registrar():
    # TODO: validar email/contraseña, hashear con bcrypt, persistir usuario
    raise NotImplementedError


@auth_bp.post("/auth/login")
def iniciar_sesion():
    # TODO: verificar credenciales vs hash, emitir JWT con rol en claims
    raise NotImplementedError


@auth_bp.get("/auth/me")
@jwt_required()
def perfil():
    return jsonify(mensaje="endpoint pendiente de implementación")