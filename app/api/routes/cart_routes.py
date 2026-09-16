from uuid import UUID

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.api.middleware.auth import requiere_sesion, usuario_actual
from app.application.carrito.gestionar_carrito import (
    GestionarCarrito,
    ItemCarritoNoEncontrado,
)
from app.application.catalogo_stock.gestionar_producto import GestionarProducto
from app.application.common.dto import ActualizarProductoDTO

cart_bp = Blueprint("carrito", __name__)


def _servicio() -> GestionarCarrito:
    """Servicio de carrito inyectado desde el punto de composición
    (`create_app`), para que esta capa no dependa de `infrastructure`."""
    return current_app.config["CARRITO_SERVICE"]


def _servicio_producto() -> GestionarProducto:
    """Servicio de catálogo (productos) inyectado desde `create_app`.

    Lo usa la finalización de compra mock para validar y descontar stock,
    respetando la capa Clean Architecture (api → application, nunca infra)."""
    return current_app.config["PRODUCTO_SERVICE"]


def _usuario_id() -> str:
    """Identidad del usuario dueño del carrito: el X-User-Id del gateway.

    El carrito se persiste por usuario real (FK `carrito.usuario_id` →
    `usuarios.id`), por eso todos los endpoints exigen sesión (requiere_sesion).
    """
    return usuario_actual()


def _datos_json() -> dict:
    """Punto único de entrada para el input de cada endpoint.
    # TODO: input validation / sanitización aquí (fase de hardening).
    """
    return request.get_json(silent=True) or {}


def _a_publico(carrito) -> dict:
    return {
        "usuario_id": carrito.usuario_id,
        "items": [
            {
                "id": str(item.id),
                "producto_id": item.producto_id,
                "cantidad": item.cantidad,
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

    try:
        carrito = _servicio().agregar_item(_usuario_id(), producto_id, cantidad)
    except ValueError as exc:
        return _error(str(exc), 400)
    except IntegrityError as exc:
        # FK `carrito_items.producto_id` -> `productos.id`: el producto no existe.
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


@cart_bp.post("/cart/finalizar-compra-mock")
@requiere_sesion()
def finalizar_compra_mock():
    # TODO: MOCK TEMPORAL — simula la venta completada.
    # Cuando aterricen los casos de uso de pedidos/pago este endpoint debe
    # desaparecer y reemplazarse por `POST /api/pago/crear` + `confirmar`.
    # Acá se valida el stock de TODOS los items antes de descontar nada
    # (para no dejar un carrito a medias) y se vacía el carrito al final.
    usuario = _usuario_id()
    carrito = _servicio().obtener(usuario)
    if not carrito.items:
        return _error("No hay productos en el carrito para finalizar la compra", 400)

    lineas = []
    for item in carrito.items:
        try:
            producto_id = UUID(str(item.producto_id))
        except ValueError:
            return _error("El carrito contiene un producto inválido", 400)
        producto = _servicio_producto().consultar(producto_id)
        if producto is None:
            return _error("Uno de los productos del carrito ya no existe", 409)
        if producto.stock < item.cantidad:
            return _error(
                f"No hay stock suficiente de «{producto.nombre}» "
                f"(disponible: {producto.stock})",
                409,
            )
        lineas.append((producto, item.cantidad))

    for producto, cantidad in lineas:
        _servicio_producto().actualizar(
            ActualizarProductoDTO(id=producto.id, stock=producto.stock - cantidad)
        )

    _servicio().vaciar(usuario)
    return jsonify(
        mensaje="Compra finalizada con éxito",
        items=[
            {"producto_id": str(p.id), "nombre": p.nombre, "cantidad": c}
            for p, c in lineas
        ],
    )