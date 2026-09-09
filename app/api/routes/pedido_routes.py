from flask import Blueprint, jsonify

pedido_bp = Blueprint("pedidos", __name__)


@pedido_bp.post("/pedidos")
def crear_pedido():
    raise NotImplementedError


@pedido_bp.get("/pedidos/<uuid:pedido_id>")
def detalle_pedido(pedido_id):
    raise NotImplementedError


@pedido_bp.post("/pago/crear")
def crear_pago():
    # TODO: body {items, total, cliente} -> {url, token}
    raise NotImplementedError


@pedido_bp.post("/pago/confirmar")
def confirmar_pago():
    raise NotImplementedError