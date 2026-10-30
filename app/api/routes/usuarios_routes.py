from uuid import UUID

from flask import Blueprint, current_app, jsonify, request

from app.api.middleware.auth import requiere_sesion, rol_requerido, usuario_actual
from app.application.usuarios.gestionar_usuarios import (
    CorreoEnUso,
    DatosUsuarioInvalidos,
    GestionarUsuarios,
    OperacionNoPermitida,
    UsuarioNoEncontrado,
)

usuarios_bp = Blueprint("usuarios", __name__)


def _servicio() -> GestionarUsuarios:
    """Caso de uso inyectado desde `create_app` (la ruta no importa infraestructura)."""
    return current_app.config["USUARIOS_SERVICE"]


def _cuerpo() -> dict:
    return request.get_json(silent=True) or {}


def _error(exc: Exception, status: int):
    """Formato de error acordado con el frontend: `{ mensaje }`."""
    return jsonify(mensaje=str(exc)), status


@usuarios_bp.get("/usuarios")
@requiere_sesion()
@rol_requerido("admin")
def listar_usuarios():
    """Usuarios vivos con sus metricas de compras y cotizaciones (solo admin).

    Devuelve `{usuarios: [...]}` para que el frontend distinga el listado
    vacio de un error.
    """
    return jsonify(usuarios=_servicio().listar())


@usuarios_bp.post("/usuarios")
@requiere_sesion()
@rol_requerido("admin")
def crear_usuario():
    """Alta de usuario desde el panel (solo admin).

    Body: `{nombre, apellido, email, password, rol}`. La contrasena se guarda
    hasheada con bcrypt (mismo formato que el gateway) y el correo es unico.
    """
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
def cambiar_rol(usuario_id: UUID):
    """Otorga o quita permisos (admin <-> cliente) sin dejar el sistema sin admin."""
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
def cambiar_estado(usuario_id: UUID):
    """Bloquea (`{activo: false}`) o desbloquea (`{activo: true}`) una cuenta.

    El bloqueo es reversible y no borra datos; el gateway rechaza el login de
    las cuentas inactivas.
    """
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
def eliminar_usuario(usuario_id: UUID):
    """Eliminacion logica (soft delete) de una cuenta.

    La fila se conserva porque pedidos y cotizaciones la referencian; se marca
    `eliminado_en` y se desactiva el acceso.
    """
    try:
        _servicio().eliminar(usuario_id, usuario_actual())
    except UsuarioNoEncontrado as exc:
        return _error(exc, 404)
    except OperacionNoPermitida as exc:
        return _error(exc, 409)
    return jsonify(mensaje="Usuario eliminado")
