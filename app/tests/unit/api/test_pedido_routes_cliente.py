"""`_cliente` no puede romper un listado de pedidos por un dato viejo.

`direccion_envio` es un `Text` con el cliente serializado a mano por el caso de
uso, o sea que no tiene ninguna garantía de que siga siendo JSON válido: hay
filas escritas antes de que existiera el campo, y una fila corrupta no puede
dejar de servir `GET /api/pedidos` (es un listado, no un detalle). Por eso el
helper degrada a `{}` en vez de dejar que el `json.loads` reviente el 500.

No necesita base: es una función pura sobre el `pedido`.
"""

from __future__ import annotations

import json

from app.api.routes.pedido_routes import _a_publico_pedido, _cliente


class _PedidoFalso:
    """Solo lo que `_cliente` y `_a_publico_pedido` llegan a mirar."""

    def __init__(self, direccion_envio, detalles=()):
        self.id = "00000000-0000-0000-0000-000000000001"
        self.estado = type("E", (), {"value": "pendiente"})()
        self.total = 1000
        self.entrega = "retiro"
        self.direccion_envio = direccion_envio
        self.creado_en = None
        self.codigo_seguimiento = None
        self.estado_seguimiento = None
        self.seguimiento_actualizado_en = None
        self.usuario_id = "00000000-0000-0000-0000-000000000002"
        self.detalles = list(detalles)


def test_deserializa_el_cliente_guardado():
    datos = {"nombre": "Ana", "email": "ana@ejemplo.test"}
    assert _cliente(_PedidoFalso(json.dumps(datos))) == datos


def test_sin_direccion_devuelve_vacio():
    assert _cliente(_PedidoFalso(None)) == {}


def test_json_invalido_no_rompe():
    assert _cliente(_PedidoFalso("{no es json")) == {}


def test_json_que_no_es_objeto_no_rompe():
    """Una lista o un escalar es JSON válido pero no es un cliente."""
    assert _cliente(_PedidoFalso('["Ana"]')) == {}
    assert _cliente(_PedidoFalso('"Ana"')) == {}


def test_tipo_invalido_no_rompe():
    """La columna es `Text`, pero un `None`/número no debe reventar el listado."""
    assert _cliente(_PedidoFalso(123)) == {}


def test_publico_devuelve_cliente_vacio_y_no_una_clave_rota():
    """El JSON de la API siempre tiene `cliente`, aunque no haya datos."""
    datos = _a_publico_pedido(_PedidoFalso(None))
    assert datos["cliente"] == {}
    assert "entrega" in datos