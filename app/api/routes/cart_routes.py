from uuid import UUID

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.api.middleware.auth import requiere_sesion, usuario_actual
from app.application.carrito.gestionar_carrito import (
    GestionarCarrito,
    ItemCarritoNoEncontrado,
)

cart_bp = Blueprint("carrito", __name__)


def _servicio() -> GestionarCarrito:
    return current_app.config["CARRITO_SERVICE"]


def _usuario_id() -> str:

    return usuario_actual()


def _datos_json() -> dict:
    return request.get_json(silent=True) or {}


def _a_publico(carrito) -> dict:
    return {
        "usuario_id": carrito.usuario_id,
        "items": [
            {
                "id": str(item.id),
                "producto_id": item.producto_id,
                "cantidad": item.cantidad,
                "color": item.color,
                "imagen": item.imagen,
            }
            for item in carrito.items
        ],
    }


def _error(msg: str, estado: int):
    return jsonify(mensaje=msg), estado


@cart_bp.post("/cart/items")
@requiere_sesion()
def agregar_producto():
    datos = _datos_json()
    if "producto_id" not in datos:
        return _error("producto_id y cantidad son obligatorios", 400)
    try:
        cantidad = int(datos.get("cantidad", 1))
    except (TypeError, ValueError):
        return _error("cantidad debe ser un número entero", 400)
    try:
        producto_id = str(UUID(str(datos["producto_id"])))
    except (TypeError, ValueError):
        return _error("producto_id debe ser un UUID válido", 400)

    color = datos.get("color")
    if color is not None and not isinstance(color, str):
        return _error("color debe ser un texto", 400)
    if isinstance(color, str) and len(color.strip()) > 50:
        return _error("color no puede superar los 50 caracteres", 400)

    try:
        carrito = _servicio().agregar_item(
            _usuario_id(), producto_id, cantidad, color
        )
    except ValueError as exc:
        return _error(str(exc), 400)
    except IntegrityError as exc:
        if "FK_CARRITO_ITEM_PRODUCTO" in str(exc.orig):
            return _error("El producto no existe en el catálogo", 404)
        raise
    return jsonify(carrito=_a_publico(carrito)), 201


@cart_bp.get("/cart")
@requiere_sesion()
def consultar_carrito():
    carrito = _servicio().obtener(_usuario_id())
    return jsonify(carrito=_a_publico(carrito))


@cart_bp.put("/cart/items/<uuid:item_id>")
@requiere_sesion()
def modificar_cantidad(item_id: UUID):
    datos = _datos_json()
    try:
        cantidad = int(datos.get("cantidad"))
    except (TypeError, ValueError):
        return _error("cantidad es obligatoria", 400)

    try:
        carrito = _servicio().actualizar_cantidad(_usuario_id(), item_id, cantidad)
    except ValueError as exc:
        return _error(str(exc), 400)
    except ItemCarritoNoEncontrado:
        return _error("Ítem del carrito no encontrado", 404)
    return jsonify(carrito=_a_publico(carrito))


@cart_bp.delete("/cart/items/<uuid:item_id>")
@requiere_sesion()
def quitar_producto(item_id: UUID):
    try:
        carrito = _servicio().eliminar_item(_usuario_id(), item_id)
    except ItemCarritoNoEncontrado:
        return _error("Ítem del carrito no encontrado", 404)
    return jsonify(carrito=_a_publico(carrito))


@cart_bp.delete("/cart")
@requiere_sesion()
def vaciar_carrito():
    carrito = _servicio().vaciar(_usuario_id())
    return jsonify(carrito=_a_publico(carrito))