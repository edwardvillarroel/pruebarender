"""`_a_publico_pedido` debe exponer la foto de cada línea del pedido.

La imagen la resuelve `PedidoRepository` al leer (una ruta de BLOB, no los
bytes) y la ruta solo la reenvía tal cual. Sin este campo el frontend no tiene
de dónde sacar la miniatura y cae al icono genérico del modal de MisPedidos.

No necesita base: es una función pura sobre el `pedido`.
"""

from __future__ import annotations

from app.api.routes.pedido_routes import _a_publico_pedido

_RUTA_COLOR = "/api/productos/colores/00000000-0000-0000-0000-0000000000aa/imagen"


class _DetalleFalso:
    """Solo lo que `_a_publico_pedido` llega a mirar de un detalle."""

    def __init__(self, imagen):
        self.producto_id = "00000000-0000-0000-0000-000000000010"
        self.cantidad = 2
        self.precio_unitario = 5000
        self.nombre = "Llavero"
        self.color = "Rojo"
        self.imagen = imagen


class _PedidoFalso:
    def __init__(self, detalles=()):
        self.id = "00000000-0000-0000-0000-000000000001"
        self.estado = type("E", (), {"value": "pendiente"})()
        self.total = 10000
        self.entrega = "retiro"
        self.direccion_envio = None
        self.creado_en = None
        self.codigo_seguimiento = None
        self.estado_seguimiento = None
        self.transportista = None
        self.seguimiento_actualizado_en = None
        self.usuario_id = "00000000-0000-0000-0000-000000000002"
        self.detalles = list(detalles)
        self.resenas_pendientes = 0


def test_item_incluye_la_ruta_de_la_imagen():
    datos = _a_publico_pedido(_PedidoFalso([_DetalleFalso(_RUTA_COLOR)]))
    assert datos["items"][0]["imagen"] == _RUTA_COLOR


def test_item_sin_imagen_queda_en_none():
    datos = _a_publico_pedido(_PedidoFalso([_DetalleFalso(None)]))
    assert datos["items"][0]["imagen"] is None
