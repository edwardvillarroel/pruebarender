"""Rutas de pedidos y pagos (TUU).

`/pedidos` exigen sesión (cabecera X-User-Id). Las notificaciones de la
pasarela (`/pago/callback`) y la confirmación del navegador (`/pago/confirmar`)
no exigen sesión: se validan por la firma HMAC de TUU.
"""

from __future__ import annotations

from uuid import UUID

from flask import Blueprint, current_app, jsonify, request

from app.api.middleware.auth import requiere_sesion, usuario_actual
from app.application.common.dto import CrearPedidoDTO, IniciarPagoDTO, ItemPedidoDTO
from app.application.pedidos_pagos.crear_pedido import CrearPedido
from app.application.pedidos_pagos.consultar_pedido import ConsultarPedido
from app.application.pedidos_pagos.procesar_pago import ProcesarPago
from app.domain.interfaces.pasarela_pago import ErrorPasarela

pedido_bp = Blueprint("pedidos", __name__)


def _servicio_pedido() -> CrearPedido:
    return current_app.config["PEDIDO_SERVICE"]


def _servicio_consulta() -> ConsultarPedido:
    return current_app.config["CONSULTA_PEDIDO_SERVICE"]


def _servicio_pago() -> ProcesarPago:
    return current_app.config["PAGO_SERVICE"]


def _error(msg: str, estado: int):
    return jsonify(mensaje=msg), estado


def _usuario_uuid() -> UUID:
    """Id del usuario de la sesión como UUID (el carrito lo guarda así)."""
    return UUID(str(usuario_actual()))


def _items(datos: dict) -> list[ItemPedidoDTO]:
    """Convierte `items` del body a DTO de dominio.

    Cada ítem usa `id` (producto) y `cantidad`; el precio nunca se toma del
    cliente, lo recalcula la capa de aplicación desde la base de datos.
    """
    items: list[ItemPedidoDTO] = []
    for raw in datos.get("items") or []:
        if not isinstance(raw, dict) or "id" not in raw:
            raise ValueError("Cada ítem requiere «id» (producto) y «cantidad»")
        try:
            producto_id = UUID(str(raw["id"]))
            cantidad = int(raw.get("cantidad", 1))
        except (TypeError, ValueError):
            raise ValueError("Ítem con id o cantidad inválidos")
        if cantidad < 1:
            raise ValueError("La cantidad debe ser un entero mayor a cero")
        items.append(ItemPedidoDTO(producto_id=producto_id, cantidad=cantidad))
    return items


def _a_publico_pedido(pedido) -> dict:
    return {
        "id": str(pedido.id),
        "estado": pedido.estado.value,
        "total": pedido.total,
        "fecha": pedido.creado_en.isoformat() if pedido.creado_en else None,
        "items": [
            {
                "producto_id": str(detalle.producto_id),
                "cantidad": detalle.cantidad,
                "precio_unitario": detalle.precio_unitario,
            }
            for detalle in pedido.detalles
        ],
    }


def _es_dueno(pedido) -> bool:
    if usuario_actual() == str(pedido.usuario_id):
        return True
    return request.headers.get("X-User-Rol") == "admin"


@pedido_bp.post("/pedidos")
@requiere_sesion()
def crear_pedido():
    """Crea un pedido sin pago (venta local/administrativa)."""
    datos = request.get_json(silent=True) or {}
    try:
        dto = CrearPedidoDTO(
            usuario_id=_usuario_uuid(),
            items=_items(datos),
            entrega=str(datos.get("entrega") or "retiro"),
            cliente=datos.get("cliente"),
        )
    except (ValueError, TypeError) as exc:
        return _error(f"Datos inválidos: {exc}", 400)
    try:
        pedido = _servicio_pedido().ejecutar(dto)
    except ValueError as exc:
        return _error(str(exc), 409)
    return jsonify(_a_publico_pedido(pedido)), 201


@pedido_bp.get("/pedidos")
@requiere_sesion()
def listar_pedidos():
    try:
        usuario_id = _usuario_uuid()
    except (ValueError, TypeError):
        return _error("Sesión inválida", 401)
    pedidos = _servicio_consulta().del_usuario(usuario_id)
    return jsonify(pedidos=[_a_publico_pedido(p) for p in pedidos])


@pedido_bp.get("/pedidos/<uuid:pedido_id>")
@requiere_sesion()
def detalle_pedido(pedido_id: UUID):
    pedido = _servicio_consulta().por_id(pedido_id)
    if pedido is None:
        return _error("Pedido no encontrado", 404)
    if not _es_dueno(pedido):
        return _error("No autorizado", 403)
    return jsonify(_a_publico_pedido(pedido))


@pedido_bp.post("/pago/crear")
@requiere_sesion()
def crear_pago():
    """Crea pedido + pago y devuelve dónde redirigir al cliente ({url, token})."""
    datos = request.get_json(silent=True) or {}
    if not datos.get("items"):
        return _error("items es obligatorio", 400)
    try:
        dto = IniciarPagoDTO(
            usuario_id=_usuario_uuid(),
            items=_items(datos),
            entrega=str(datos.get("entrega") or "retiro"),
            cliente=datos.get("cliente"),
        )
    except (ValueError, TypeError) as exc:
        return _error(f"Datos inválidos: {exc}", 400)

    try:
        resultado = _servicio_pago().iniciar(dto)
    except ValueError as exc:
        return _error(str(exc), 409)
    except ErrorPasarela as exc:
        return _error(str(exc), 502)
    return jsonify(url=resultado.url, token=resultado.token)


def _parametros_notificacion() -> dict:
    """Parámetros x_* + firma: JSON, form-urlencoded (TUU) o query string."""
    json_body = request.get_json(silent=True)
    if json_body:
        return json_body
    form = request.form.to_dict()
    if form:
        return form
    return request.args.to_dict()


@pedido_bp.post("/pago/confirmar")
def confirmar_pago():
    """Confirma el resultado del pago en el navegador (redirección de TUU)."""
    try:
        resultado = _servicio_pago().confirmar(_parametros_notificacion())
    except ErrorPasarela as exc:
        return _error(str(exc), 400)
    return jsonify(
        estado=resultado.estado,
        pedido_id=resultado.pedido_id,
        mensaje=resultado.mensaje,
    )


@pedido_bp.post("/pago/callback")
def callback_pago():
    """Notificación server-to-server de TUU (fuente de verdad del pago)."""
    try:
        resultado = _servicio_pago().confirmar(_parametros_notificacion())
    except ErrorPasarela as exc:
        return _error(str(exc), 400)
    return jsonify(resultado=resultado.estado)