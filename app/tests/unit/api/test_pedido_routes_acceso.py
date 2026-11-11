"""Control de acceso en las rutas de pedidos (OWASP Top 10 2025, A01).

`GET /api/pedidos/<uuid>`, `POST .../cancelar`, `DELETE .../pagar` y los
endpoint de pago/evaluacion de documentos solo deben servir al dueño del
pedido o a un admin. El dueño se deriva del `X-User-Id` que el gateway
inyecta tras validar el JWT: un id arbitrario en la URL no debe abrir el
detalle (eso es lo que el OWASP Top 10 llama Broken Access Control /
Insecure Direct Object Reference).

No necesita base de datos: los servicios se mockean via `app.config[...]`.
"""

from unittest.mock import Mock
from uuid import uuid4

from app.application.pedidos_pagos.cambiar_estado_pedido import (
    PedidoDeOtroUsuarioError,
)
from app.application.pedidos_pagos.gestionar_pedido_no_pagado import (
    PedidoNoPagadoDeOtroUsuarioError,
)


# OWASP A01: el backend es fail-closed, toda request autenticada debe venir
# firmada por el gateway con `X-Internal-Secret` (fijado por el conftest).
CABECERA_USUARIO = {
    "X-User-Id": "11111111-1111-1111-1111-111111111111",
    "X-User-Rol": "cliente",
    "X-Internal-Secret": "secreto-interno-test",
}
CABECERA_ADMIN = {
    "X-User-Id": "11111111-1111-1111-1111-111111111111",
    "X-User-Rol": "admin",
    "X-Internal-Secret": "secreto-interno-test",
}


class _PedidoFalso:
    """Solo los atributos que `_a_publico_pedido` lee del pedido."""

    def __init__(self, usuario_id: str):
        self.id = str(uuid4())
        self.cotizacion_id = None
        self.estado = type("E", (), {"value": "pendiente"})()
        self.total = 1000.0
        self.subtotal = 1000.0
        self.descuento_productos = 0.0
        self.descuento_cupon = 0.0
        self.cupon_codigo = None
        self.entrega = "retiro"
        self.tipo_documento = None
        self.direccion_envio = None
        self.creado_en = None
        self.codigo_seguimiento = None
        self.transportista = None
        self.estado_seguimiento = None
        self.seguimiento_actualizado_en = None
        self.detalles = []
        self.resenas_pendientes = 0
        self.resenas_completadas = 0
        self.estado_pago = None
        self.aviso_cancelacion_en = None
        self.aviso_cancelacion_visto = False
        self.usuario_id = usuario_id


def _uuid_pedido() -> str:
    return str(uuid4())


def _configurar_consulta(app, pedido) -> None:
    servicio = Mock()
    servicio.por_id.return_value = pedido
    app.config["CONSULTA_PEDIDO_SERVICE"] = servicio


# ---------------------------------------------------------------------------
# GET /api/pedidos (listado: siempre del usuario autenticado)
# ---------------------------------------------------------------------------


def test_listado_de_pedidos_requiere_sesion(app, client):
    respuesta = client.get("/api/pedidos")
    assert respuesta.status_code == 401
    assert respuesta.get_json()["mensaje"] == "Sesión requerida"


# ---------------------------------------------------------------------------
# GET /api/pedidos/<uuid:pedido_id>
# ---------------------------------------------------------------------------


def test_detalle_pedido_sin_sesion_es_401(app, client):
    respuesta = client.get(f"/api/pedidos/{_uuid_pedido()}")
    assert respuesta.status_code == 401
    assert respuesta.get_json()["mensaje"] == "Sesión requerida"


def test_detalle_pedido_de_otro_usuario_es_403(app, client):
    """El dueño real viene del JWT/gateway, no del path: otro user -> 403."""
    _configurar_consulta(app, _PedidoFalso("22222222-2222-2222-2222-222222222222"))

    respuesta = client.get(
        f"/api/pedidos/{_uuid_pedido()}", headers=CABECERA_USUARIO
    )

    assert respuesta.status_code == 403
    assert respuesta.get_json()["mensaje"] == "No autorizado"


def test_detalle_pedido_del_propio_usuario_es_200(app, client):
    _configurar_consulta(app, _PedidoFalso(CABECERA_USUARIO["X-User-Id"]))

    respuesta = client.get(f"/api/pedidos/{_uuid_pedido()}", headers=CABECERA_USUARIO)

    assert respuesta.status_code == 200
    assert respuesta.get_json()["id"]


def test_detalle_pedido_admin_puede_ver_de_otro_usuario(app, client):
    """El admin (rol del gateway) puede ver el detalle de cualquier pedido."""
    _configurar_consulta(app, _PedidoFalso("22222222-2222-2222-2222-222222222222"))

    respuesta = client.get(f"/api/pedidos/{_uuid_pedido()}", headers=CABECERA_ADMIN)

    assert respuesta.status_code == 200
    assert respuesta.get_json()["id"]


# ---------------------------------------------------------------------------
# POST /api/pedidos/<uuid:pedido_id>/cancelar
# ---------------------------------------------------------------------------


def test_cancelar_pedido_sin_sesion_es_401(app, client):
    respuesta = client.post(f"/api/pedidos/{_uuid_pedido()}/cancelar", json={})
    assert respuesta.status_code == 401
    assert respuesta.get_json()["mensaje"] == "Sesión requerida"


def test_cancelar_pedido_de_otro_usuario_es_403(app, client):
    servicio = Mock()
    servicio.cancelar.side_effect = PedidoDeOtroUsuarioError("No autorizado")
    app.config["CAMBIAR_ESTADO_PEDIDO_SERVICE"] = servicio

    respuesta = client.post(
        f"/api/pedidos/{_uuid_pedido()}/cancelar",
        json={},
        headers=CABECERA_USUARIO,
    )

    assert respuesta.status_code == 403
    assert respuesta.get_json()["mensaje"] == "No autorizado"


# ---------------------------------------------------------------------------
# DELETE /api/pedidos/<uuid:pedido_id>
# ---------------------------------------------------------------------------


def test_eliminar_pedido_de_otro_usuario_es_403(app, client):
    servicio = Mock()
    servicio.eliminar.side_effect = PedidoNoPagadoDeOtroUsuarioError("No autorizado")
    app.config["PEDIDO_NO_PAGADO_SERVICE"] = servicio

    respuesta = client.delete(
        f"/api/pedidos/{_uuid_pedido()}",
        headers=CABECERA_USUARIO,
    )

    assert respuesta.status_code == 403
    assert respuesta.get_json()["mensaje"] == "No autorizado"


# ---------------------------------------------------------------------------
# POST /api/pedidos/<uuid:pedido_id>/pagar (reintento de pago)
# ---------------------------------------------------------------------------


def test_reintentar_pago_de_otro_usuario_es_403(app, client):
    servicio = Mock()
    servicio.reintentar.side_effect = PedidoNoPagadoDeOtroUsuarioError("No autorizado")
    app.config["PEDIDO_NO_PAGADO_SERVICE"] = servicio

    respuesta = client.post(
        f"/api/pedidos/{_uuid_pedido()}/pagar",
        json={"items": []},
        headers=CABECERA_USUARIO,
    )

    assert respuesta.status_code == 403
    assert respuesta.get_json()["mensaje"] == "No autorizado"
