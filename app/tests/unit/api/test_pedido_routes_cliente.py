


from __future__ import annotations

import json

from app.api.routes.pedido_routes import _a_publico_pedido, _cliente


class _PedidoFalso:

    def __init__(self, direccion_envio, detalles=()):
        self.id = "00000000-0000-0000-0000-000000000001"
        self.cotizacion_id = None
        self.estado = type("E", (), {"value": "pendiente"})()
        self.total = 1000
        self.subtotal = 1000
        self.descuento_productos = 0
        self.descuento_cupon = 0
        self.cupon_codigo = None
        self.entrega = "retiro"
        self.direccion_envio = direccion_envio
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


def test_deserializa_el_cliente_guardado():
    datos = {"nombre": "Ana", "email": "ana@ejemplo.test"}
    assert _cliente(_PedidoFalso(json.dumps(datos))) == datos


def test_sin_direccion_devuelve_vacio():
    assert _cliente(_PedidoFalso(None)) == {}


def test_json_invalido_no_rompe():
    assert _cliente(_PedidoFalso("{no es json")) == {}


def test_json_que_no_es_objeto_no_rompe():
    assert _cliente(_PedidoFalso('["Ana"]')) == {}
    assert _cliente(_PedidoFalso('"Ana"')) == {}


def test_tipo_invalido_no_rompe():
    assert _cliente(_PedidoFalso(123)) == {}


def test_publico_devuelve_cliente_vacio_y_no_una_clave_rota():
    datos = _a_publico_pedido(_PedidoFalso(None))
    assert datos["cliente"] == {}
    assert "entrega" in datos