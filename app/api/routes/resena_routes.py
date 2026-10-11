"""Rutas de reseñas (estrellas 1-5) por pedido.

`POST /api/pedidos/<id>/resenas` solo del dueño y solo con el pedido
`entregado`; `GET` para la precarga del modal, disponible también para admin
(mismo criterio que `_es_dueno` en `pedido_routes`). El frontend decide qué
mostrar según el status HTTP, así que cada código tiene un significado fijo:
400 datos · 403 no dueño · 404 pedido o producto · 409 no entregado o ya
reseñado.
"""

from __future__ import annotations

from uuid import UUID

from flask import Blueprint, current_app, jsonify, request

from app.api.middleware.auth import requiere_sesion, usuario_actual
from app.application.resenas.gestionar_resena import (
    ComentarioInvalidoError,
    EstrellasInvalidasError,
    GestionarResena,
    NoAutorizadoError,
    NoEntregadoError,
    PedidoNoEncontradoError,
    ProductoNoEnPedidoError,
)
from app.domain.entities.resena import ResenaPublica
from app.domain.interfaces.repositories import ResenaDuplicadaError

resenas_bp = Blueprint("resenas", __name__)


def _servicio_resena() -> GestionarResena:
    """Servicio inyectado desde `create_app` (la capa API no depende de
    `infrastructure`)."""
    return current_app.config["RESENA_SERVICE"]


def _error(msg: str, estado: int):
    return jsonify(mensaje=msg), estado


def _usuario_uuid() -> UUID:
    return UUID(str(usuario_actual()))


def _a_publico_resena(resena) -> dict:
    return {
        "id": str(resena.id),
        "producto_id": str(resena.producto_id),
        "estrellas": resena.estrellas,
        "comentario": resena.comentario,
        "creado_en": resena.creado_en.isoformat() if resena.creado_en else None,
    }


def _a_publico_resena_producto(resena: ResenaPublica) -> dict:
    return {
        "id": str(resena.id),
        "producto_id": str(resena.producto_id),
        "estrellas": resena.estrellas,
        "comentario": resena.comentario,
        "creado_en": resena.creado_en.isoformat() if resena.creado_en else None,
        "autor": resena.autor,
    }


@resenas_bp.post("/pedidos/<uuid:pedido_id>/resenas")
@requiere_sesion()
def crear_resena(pedido_id: UUID):
    datos = request.get_json(silent=True) or {}
    try:
        usuario_id = _usuario_uuid()
    except (TypeError, ValueError):
        return _error("Sesión inválida", 401)
    try:
        producto_id = UUID(str(datos.get("producto_id")))
    except (TypeError, ValueError):
        return _error("producto_id inválido", 400)
    estrellas = datos.get("estrellas")
    comentario = datos.get("comentario")
    try:
        resena = _servicio_resena().registrar(
            usuario_id, pedido_id, producto_id, estrellas, comentario
        )
    except EstrellasInvalidasError as exc:
        return _error(str(exc), 400)
    except ComentarioInvalidoError as exc:
        return _error(str(exc), 400)
    except PedidoNoEncontradoError as exc:
        return _error(str(exc), 404)
    except NoAutorizadoError as exc:
        return _error(str(exc), 403)
    except NoEntregadoError as exc:
        return _error(str(exc), 409)
    except ProductoNoEnPedidoError as exc:
        return _error(str(exc), 404)
    except ResenaDuplicadaError as exc:
        return _error(str(exc), 409)
    return jsonify(_a_publico_resena(resena)), 201


@resenas_bp.get("/pedidos/<uuid:pedido_id>/resenas")
@requiere_sesion()
def listar_resenas_pedido(pedido_id: UUID):
    try:
        usuario_id = _usuario_uuid()
    except (TypeError, ValueError):
        return _error("Sesión inválida", 401)
    es_admin = request.headers.get("X-User-Rol") == "admin"
    try:
        resenas = _servicio_resena().listar_por_pedido(
            usuario_id, pedido_id, es_admin=es_admin
        )
    except PedidoNoEncontradoError as exc:
        return _error(str(exc), 404)
    except NoAutorizadoError as exc:
        return _error(str(exc), 403)
    return jsonify(resenas=[_a_publico_resena(r) for r in resenas])


@resenas_bp.get("/productos/<uuid:producto_id>/resenas")
def listar_resenas_producto(producto_id: UUID):
    # 404 si el producto no existe; si existe, lista (posiblemente vacia).
    if current_app.config["PRODUCTO_SERVICE"].consultar(producto_id) is None:
        return _error("Producto no encontrado", 404)
    resenas = _servicio_resena().listar_por_producto(producto_id)
    return jsonify(resenas=[_a_publico_resena_producto(r) for r in resenas])
