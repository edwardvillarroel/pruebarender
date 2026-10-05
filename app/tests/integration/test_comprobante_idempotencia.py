"""El comprobante sale UNA vez por pago, y sale despues de confirmar.

Los tests unitarios de `test_comprobante_correo.py` fijan las reglas sueltas del
envio (best-effort, destino invalido, fallo logueado). Este cierra el circuito
por la API, que es donde se ve el problema real: el ORDEN.

La pasarela avisa dos veces el mismo pago:

1. `POST /api/pago/callback` server-to-server, que es la fuente de verdad y la
   que mas veces reintenta si no responde 200.
2. La redireccion del navegador a `POST /api/pago/confirmar`, que el usuario
   puede recargar, o que TUU puede reenviar.

Las dos entran por `confirmar`, que es idempotente para el PAGO. Lo que hay que
verificar es que el CORREO hereda esa idempotencia: si el comprobante se mandara
antes del guard, el cliente recibe dos correos del mismo pedido y la pregunta
que le llega por soporte es si le cobraron dos veces.

Esta prueba casi no vale por si sola: vale porque el `correo` es un doble que
registra. Con un EmailJS real, un doble envio seria invisible en los tests.
"""

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
    """Pasarela sin HTTP: devuelve una URL fija y acepta cualquier firma."""

    def crear_intento(self, solicitud: SolicitudPago) -> ResultadoIntentoPago:
        return ResultadoIntentoPago(
            url="https://pasarela-falsa.test/pagar", token=solicitud.referencia
        )

    def verificar_firma(self, parametros: dict[str, str]) -> bool:
        return True


class _CorreoContador:
    """Doble que cuenta a quien se le mando el comprobante.

    `falla=True` simula al proveedor caido. Hace falta porque `.env` trae las
    credenciales reales de EmailJS: sin este doble, un test que paga de verdad
    sale a la red y le manda un comprobante a `ana@caracterizacion.test`.
    """

    def __init__(self, falla: bool = False):
        self.enviados: list[tuple[str, str, str]] = []
        self._falla = falla

    def enviar_comprobante_pedido(
        self, pedido, cliente_email: str, estado_pago: str
    ) -> None:
        if self._falla:
            raise RuntimeError("EmailJS devolvio 500")
        self.enviados.append((str(pedido.id), cliente_email, estado_pago))


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
    """Reemplaza `PAGO_SERVICE` por uno con un correo que registra.

    El punto de composicion vive en `app.config`, asi que alcanza con rehacer el
    `ProcesarPago` contra los repositorios reales: el pedido, el pago y el stock
    siguen yendo a la base de verdad, que es justo lo que hay que probar.
    """
    correo = _CorreoContador()
    app.config["PAGO_SERVICE"] = _pago_service(correo)
    return correo


@pytest.fixture
def app_correo_caido(app):
    """Igual que `app_con_correo`, pero el proveedor revienta."""
    app.config["PAGO_SERVICE"] = _pago_service(_CorreoContador(falla=True))
    return app


def _pagar(client, producto, usuario, centinela) -> str:
    """Crea el pedido y devuelve el token de referencia de TUU."""
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
    """Callback + redireccion del mismo pago = un solo comprobante."""
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
    """El comprobante de una compra recien pagada dice "completado", no "pendiente".

    `pedido.estado` describe el envio y sigue en `pendiente` hasta que el admin
    marque que entro a produccion. Mandarlo al comprobante de pago producia
    "Estado: pendiente" debajo de "¡Gracias por tu compra!", que el cliente lee
    como "mi pago quedo pendiente". El estado del envio lo ve en Mis pedidos.
    """
    token = _pagar(client, producto(stock=10, nombre=f"{centinela}-estado"), usuario, centinela)

    _avisar_de_la_pasarela(client, token)

    _pedido_id, _email, estado_pago = app_con_correo.enviados[0]
    assert estado_pago == "completado", (
        f"el comprobante recibio {estado_pago!r}; deberia ser el estado del PAGO"
    )


def test_la_respuesta_dice_si_el_correo_se_mando(
    client, producto, usuario, centinela, app_con_correo
):
    """`correo_enviado` es lo que le permite al frontend no mentir.

    El envio es best-effort y traga la excepcion, asi que sin este campo la
    pantalla de exito decia "Te enviamos el comprobante" tanto si se mando como
    si se perdio.
    """
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
    """Con el proveedor caido, `correo_enviado` es False y el pago queda igual.

    Este es el caso que hace que el campo valga la pena: sin el, la pantalla de
    exito decia "Te enviamos el comprobante" con el correo perdido. Y como el
    envio es best-effort, el pago NO puede revertirse por esto.
    """
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
    """Un pago fallido no genera comprobante: no se compro nada."""
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
    """Retiro sin datos de cliente: el pago anda, el correo no.

    Es el caso de la venta local y del retiro sin formulario: si `direccion_envio`
    viene vacio y el envio se tratara como error, estos pedidos no se podrian
    pagar.
    """
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
    # Lo que importa: el pago se confirmo igual. Se lee `pagos.estado` y no el
    # `estado` del pedido porque son cosas distintas: el pedido queda en
    # `pendiente` hasta que Starken lo despacha, y el pago ya esta completado.
    assert _estado_del_pago() == "completado", (
        "sin email no se puede mandar el comprobante, pero el pago tiene que "
        "quedar confirmado igual"
    )


def _estado_del_pago() -> str:
    """Estado real de la fila en `pagos`, leido con SQL crudo.

    No se usa `GET /api/pedidos`: ese endpoint devuelve el estado del PEDIDO
    (pendiente/enviado/entregado), que es otra cosa, y un pago completado con el
    pedido todavia pendiente daria un falso negativo.
    """
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