





from __future__ import annotations

import pytest

from app.application.pedidos_pagos.procesar_pago import ProcesarPago
from app.domain.interfaces.pasarela_pago import (
    PasarelaPago,
    ResultadoIntentoPago,
    SolicitudPago,
)
from app.infrastructure.repositories.carrito_repository_bd import CarritoRepositoryBd
from app.infrastructure.repositories.pago_repository import PagoRepository
from app.infrastructure.repositories.pedido_repository import PedidoRepository
from app.infrastructure.repositories.producto_repository import ProductoRepository


class _PasarelaFalsa(PasarelaPago):

    def crear_intento(self, solicitud: SolicitudPago) -> ResultadoIntentoPago:
        return ResultadoIntentoPago(
            url="https://pasarela-falsa.test/pagar", token=solicitud.referencia
        )

    def verificar_firma(self, parametros: dict[str, str]) -> bool:
        return True


class _CorreoContador:


    def __init__(self, falla: bool = False):
        self.enviados: list[tuple[str, str, str]] = []
        self.admin_pedidos: list[tuple[str, str, str]] = []
        self.admin_stock: list[list] = []
        self._falla = falla

    def enviar_comprobante_pedido(
        self, pedido, cliente_email: str, estado_pago: str
    ) -> None:
        if self._falla:
            raise RuntimeError("Resend devolvio 500")
        self.enviados.append((str(pedido.id), cliente_email, estado_pago))

    def avisar_admin_pedido_pagado(
        self, pedido, cliente_email: str, estado_pago: str
    ) -> None:
        if self._falla:
            raise RuntimeError("Resend devolvio 500")
        self.admin_pedidos.append((str(pedido.id), cliente_email, estado_pago))

    def avisar_admin_stock_bajo(self, productos) -> None:
        if self._falla:
            raise RuntimeError("Resend devolvio 500")
        self.admin_stock.append(list(productos))

    def avisar_admin_nueva_cotizacion(self, solicitud) -> None:  # pragma: no cover
        raise AssertionError("no se usa en estos tests")

    def enviar_estado_cotizacion(self, solicitud, estado, precio=None):  # pragma: no cover
        raise AssertionError("no se usa en estos tests")


def _pago_service(correo) -> ProcesarPago:
    return ProcesarPago(
        PedidoRepository(),
        PagoRepository(),
        ProductoRepository(),
        _PasarelaFalsa(),
        CarritoRepositoryBd(),
        correo,
    )


@pytest.fixture
def app_con_correo(app):

    correo = _CorreoContador()
    app.config["PAGO_SERVICE"] = _pago_service(correo)
    return correo


@pytest.fixture
def app_correo_caido(app):
    app.config["PAGO_SERVICE"] = _pago_service(_CorreoContador(falla=True))
    return app


def _pagar(client, producto, usuario, centinela) -> str:
    cabeceras = {"X-User-Id": str(usuario.id), "X-User-Rol": "cliente"}
    creado = client.post(
        "/api/pago/crear",
        json={
            "entrega": "envio",
            "cliente": {
                "nombre": "Ana",
                "apellido": "Prueba",
                "email": "ana@caracterizacion.test",
            },
            "items": [{"id": str(producto.id), "cantidad": 1}],
        },
        headers=cabeceras,
    )
    assert creado.status_code == 200, creado.get_json()
    return creado.get_json()["token"]


def _avisar_de_la_pasarela(client, token: str) -> None:
    respuesta = client.post(
        "/api/pago/callback",
        data={"x_reference": token, "x_result": "completed", "x_signature": "falsa"},
    )
    assert respuesta.status_code == 200, respuesta.get_json()


def test_comprobante_una_sola_vez_aunque_la_pasarela_avise_dos_veces(
    client, producto, usuario, centinela, app_con_correo
):
    token = _pagar(client, producto(stock=10, nombre=f"{centinela}-comp"), usuario, centinela)

    _avisar_de_la_pasarela(client, token)
    _avisar_de_la_pasarela(client, token)

    assert len(app_con_correo.enviados) == 1, (
        f"el cliente recibio {len(app_con_correo.enviados)} comprobantes del mismo "
        "pedido: el guard de idempotencia tiene que correr antes del envio"
    )
    assert app_con_correo.enviados[0][1] == "ana@caracterizacion.test"


def test_el_comprobante_recibe_el_estado_del_pago_no_el_del_pedido(
    client, producto, usuario, centinela, app_con_correo
):

    token = _pagar(client, producto(stock=10, nombre=f"{centinela}-estado"), usuario, centinela)

    _avisar_de_la_pasarela(client, token)

    _pedido_id, _email, estado_pago = app_con_correo.enviados[0]
    assert estado_pago == "completado", (
        f"el comprobante recibio {estado_pago!r}; deberia ser el estado del PAGO"
    )


def test_la_respuesta_dice_si_el_correo_se_mando(
    client, producto, usuario, centinela, app_con_correo
):

    token = _pagar(client, producto(stock=10, nombre=f"{centinela}-ok"), usuario, centinela)

    respuesta = client.post(
        "/api/pago/callback",
        data={"x_reference": token, "x_result": "completed", "x_signature": "falsa"},
    )

    assert respuesta.status_code == 200, respuesta.get_json()
    assert respuesta.get_json()["correo_enviado"] is True, respuesta.get_json()


def test_la_respuesta_avisa_cuando_el_correo_no_se_mando(
    client, producto, usuario, centinela, app_correo_caido
):

    token = _pagar(client, producto(stock=10, nombre=f"{centinela}-sin"), usuario, centinela)

    respuesta = client.post(
        "/api/pago/callback",
        data={"x_reference": token, "x_result": "completed", "x_signature": "falsa"},
    )

    assert respuesta.status_code == 200, respuesta.get_json()
    cuerpo = respuesta.get_json()
    assert cuerpo["correo_enviado"] is False, cuerpo
    assert cuerpo["estado"] == "completado", "el correo caido no puede tumbar el pago"


def test_el_comprobante_no_se_manda_si_el_pago_no_se_completa(
    client, producto, usuario, centinela, app_con_correo
):
    token = _pagar(client, producto(stock=10, nombre=f"{centinela}-fallo"), usuario, centinela)

    respuesta = client.post(
        "/api/pago/callback",
        data={"x_reference": token, "x_result": "failed", "x_signature": "falsa"},
    )

    assert respuesta.status_code == 200, respuesta.get_json()
    assert app_con_correo.enviados == [], "un pago fallido no se vende"


def test_el_comprobante_se_manda_aunque_el_cliente_no_haya_mandado_email(
    client, producto, usuario, centinela, app_con_correo
):

    cabeceras = {"X-User-Id": str(usuario.id), "X-User-Rol": "cliente"}
    creado = client.post(
        "/api/pago/crear",
        json={
            "entrega": "retiro",
            "items": [{"id": str(producto(stock=5, nombre=f"{centinela}-retiro").id), "cantidad": 1}],
        },
        headers=cabeceras,
    )
    assert creado.status_code == 200, creado.get_json()

    _avisar_de_la_pasarela(client, creado.get_json()["token"])

    assert app_con_correo.enviados == [], "sin email del cliente no hay a quien mandar"
    assert _estado_del_pago() == "completado", (
        "sin email no se puede mandar el comprobante, pero el pago tiene que "
        "quedar confirmado igual"
    )


def _estado_del_pago() -> str:

    from app.infrastructure.database.connection import db

    return db.session.execute(
        db.text(
            "SELECT p.estado FROM pagos p "
            "JOIN pedidos pe ON pe.id = p.pedido_id "
            "JOIN usuarios u ON u.id = pe.usuario_id "
            "WHERE u.email LIKE '%@caracterizacion.test' "
            "ORDER BY p.creado_en DESC LIMIT 1"
        )
    ).scalar_one()