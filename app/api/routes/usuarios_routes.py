from uuid import UUID

from flask import Blueprint, current_app, jsonify, request

from app.api.middleware.auth import requiere_sesion, rol_requerido, usuario_actual
from app.api.middleware.audit_logger import auditar
from app.application.usuarios.gestionar_usuarios import (
    CorreoEnUso,
    DatosUsuarioInvalidos,
    GestionarUsuarios,
    OperacionNoPermitida,
    UsuarioNoEncontrado,
)

usuarios_bp = Blueprint("usuarios", __name__)


def _servicio() -> GestionarUsuarios:
    return current_app.config["USUARIOS_SERVICE"]


def _cuerpo() -> dict:
    return request.get_json(silent=True) or {}


def _error(exc: Exception, status: int):
    return jsonify(mensaje=str(exc)), status


@usuarios_bp.get("/usuarios")
@requiere_sesion()
@rol_requerido("admin")
def listar_usuarios():

    return jsonify(usuarios=_servicio().listar())


@usuarios_bp.post("/usuarios")
@requiere_sesion()
@rol_requerido("admin")
@auditar("crear_usuario")
def crear_usuario():

    try:
        usuario = _servicio().crear(_cuerpo(), usuario_actual())
    except DatosUsuarioInvalidos as exc:
        return _error(exc, 400)
    except CorreoEnUso as exc:
        return _error(exc, 409)
    return jsonify(usuario=usuario), 201


@usuarios_bp.patch("/usuarios/<uuid:usuario_id>/rol")
@requiere_sesion()
@rol_requerido("admin")
@auditar("cambiar_rol")
def cambiar_rol(usuario_id: UUID):
    try:
        usuario = _servicio().cambiar_rol(
            usuario_id, _cuerpo().get("rol"), usuario_actual()
        )
    except UsuarioNoEncontrado as exc:
        return _error(exc, 404)
    except DatosUsuarioInvalidos as exc:
        return _error(exc, 400)
    except OperacionNoPermitida as exc:
        return _error(exc, 409)
    return jsonify(usuario=usuario)


@usuarios_bp.patch("/usuarios/<uuid:usuario_id>/estado")
@requiere_sesion()
@rol_requerido("admin")
@auditar("cambiar_estado_usuario")
def cambiar_estado(usuario_id: UUID):

    try:
        usuario = _servicio().cambiar_estado(
            usuario_id, _cuerpo().get("activo"), usuario_actual()
        )
    except UsuarioNoEncontrado as exc:
        return _error(exc, 404)
    except DatosUsuarioInvalidos as exc:
        return _error(exc, 400)
    except OperacionNoPermitida as exc:
        return _error(exc, 409)
    return jsonify(usuario=usuario)


@usuarios_bp.delete("/usuarios/<uuid:usuario_id>")
@requiere_sesion()
@rol_requerido("admin")
@auditar("eliminar_usuario")
def eliminar_usuario(usuario_id: UUID):

    try:
        _servicio().eliminar(usuario_id, usuario_actual())
    except UsuarioNoEncontrado as exc:
        return _error(exc, 404)
    except OperacionNoPermitida as exc:
        return _error(exc, 409)
    return jsonify(mensaje="Usuario eliminado")
