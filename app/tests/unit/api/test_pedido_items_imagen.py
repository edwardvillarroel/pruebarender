


from __future__ import annotations

from app.api.routes.pedido_routes import _a_publico_pedido

_RUTA_COLOR = "/api/productos/colores/00000000-0000-0000-0000-0000000000aa/imagen"


class _DetalleFalso:

    def __init__(self, imagen):
        self.producto_id = "00000000-0000-0000-0000-000000000010"
        self.cantidad = 2
        self.precio_unitario = 5000
        self.precio_original = None
        self.nombre = "Llavero"
        self.color = "Rojo"
        self.imagen = imagen


class _PedidoFalso:
    def __init__(self, detalles=()):
        self.id = "00000000-0000-0000-0000-000000000001"
        self.cotizacion_id = None
        self.estado = type("E", (), {"value": "pendiente"})()
        self.total = 10000
        self.subtotal = 10000
        self.descuento_productos = 0
        self.descuento_cupon = 0
        self.cupon_codigo = None
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
        self.resenas_completadas = 0
        self.tipo_documento = None
        self.estado_pago = None
        self.aviso_cancelacion_en = None
        self.aviso_cancelacion_visto = False


def test_item_incluye_la_ruta_de_la_imagen():
    datos = _a_publico_pedido(_PedidoFalso([_DetalleFalso(_RUTA_COLOR)]))
    assert datos["items"][0]["imagen"] == _RUTA_COLOR


def test_item_sin_imagen_queda_en_none():
    datos = _a_publico_pedido(_PedidoFalso([_DetalleFalso(None)]))
    assert datos["items"][0]["imagen"] is None
