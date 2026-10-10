"""El comprobante se manda despues de confirmar el pago, y nunca lo rompe.

Tres cosas se prueban aca, y las tres son caracteristicas de cuando se manda el
correo y no de que se mande:

1. **Va despues del guard de idempotencia.** La pasarela avisa dos veces
   (callback server-to-server y redireccion del navegador) y las dos llegan a
   `confirmar`. Si el comprobante se mandara antes del guard, el cliente recibe
   dos correos y la duda es si le cobraron dos veces.

2. **Es best-effort.** Si el proveedor de correo revienta, el pago YA quedo
   confirmado y descontado el stock. Revertir por un correo seria peor que el
   correo perdido, asi que la excepcion se loguea y se sigue.

3. **El email sale del JSON del cliente**, que es texto crudo y puede no ser
   JSON. Un `direccion_envio` vacio, `None` o corrupto no puede romper el pago:
   es "no hay a quien mandarle el comprobante", no un error.

Lo que NO se prueba aca es que el correo llegue: eso depende de la cuenta de
EmailJS y de la PYME. Lo que se congela es la decision y el contrato.
"""

from __future__ import annotations

import json
import uuid

import pytest

from app.application.pedidos_pagos.procesar_pago import (
    ProcesarPago,
    _email_del_cliente,
)
from app.domain.entities.pedido import Pedido
from app.domain.interfaces.pasarela_pago import PasarelaPago


class _PasarelaFalsa(PasarelaPago):
    def crear_intento(self, solicitud):  # pragma: no cover - no se usa aca
        raise AssertionError("no se deberia abrir un intento en estos tests")

    def verificar_firma(self, parametros: dict[str, str]) -> bool:
        return True


class _CorreoFalso:
    """Correo que registra a quien se le mando y si hay que hacerlo fallar."""

    def __init__(self, falla: bool = False):
        self.enviados: list[tuple[Pedido, str, str]] = []
        self._falla = falla

    def enviar_comprobante_pedido(
        self, pedido: Pedido, cliente_email: str, estado_pago: str
    ) -> None:
        if self._falla:
            raise RuntimeError("EmailJS devolvio 500")
        self.enviados.append((pedido, cliente_email, estado_pago))


@pytest.fixture
def correo() -> _CorreoFalso:
    return _CorreoFalso()


def _pedido(email_cliente: str | None, estado: str = "pendiente") -> Pedido:
    return Pedido(
        usuario_id=uuid.uuid4(),
        direccion_envio=(
            json.dumps({"email": email_cliente}) if email_cliente is not None else None
        ),
        entrega="envio",
    )


def _servicio(correo) -> ProcesarPago:
    """ProcesarPago con lo minimo: `_enviar_comprobante` solo usa el correo.

    Los repos van en `None` a proposito. Esta clase de tests es sobre cuando se
    manda el correo, no sobre la base: si el metodo empezara a consultar un
    repo, este test lo va a delatar con un `AttributeError` en vez de dejarlo
    pasar.
    """
    return ProcesarPago(
        pedidos=None,
        pagos=None,
        productos=None,
        pasarela=_PasarelaFalsa(),
        carritos=None,
        correo=correo,
    )


# --- Que se mande, y a quien ------------------------------------------------


def test_envia_el_comprobante_al_email_del_cliente(correo):
    _servicio(correo)._enviar_comprobante(_pedido("ana@caracterizacion.test"), "completado")

    assert len(correo.enviados) == 1, "no se envio ningun comprobante"
    pedido, email, _ = correo.enviados[0]
    assert email == "ana@caracterizacion.test"


def test_el_comprobante_lleva_el_estado_del_pago_no_el_del_pedido(correo):
    """El `estado` del comprobante es el del PAGO, nunca `pedido.estado`.

    `pedido.estado` describe el envio y va a seguir en "pendiente" hasta que el
    admin marque que entro a produccion. Mandarlo al comprobante de una compra
    recien pagada produce "Estado: pendiente" debajo de "¡Gracias por tu
    compra!", que el cliente lee como "mi pago quedo pendiente".
    """
    _servicio(correo)._enviar_comprobante(_pedido("ana@caracterizacion.test"), "completado")

    pedido, _, estado_pago = correo.enviados[0]
    assert pedido.estado.value == "pendiente", "el pedido sale pendiente, por diseño"
    assert estado_pago == "completado", "pero el comprobante debe reportar el pago"


def test_sin_correo_configurado_no_intenta_nada():
    """`correo=None` es el caso normal de los tests y de cualquier armado viejo.

    El default del constructor existe justamente para que nadie tenga que
    cablear el correo en un `ProcesarPago` que no lo necesita.
    """
    servicio = ProcesarPago(
        pedidos=None,
        pagos=None,
        productos=None,
        pasarela=_PasarelaFalsa(),
        carritos=None,
    )

    servicio._enviar_comprobante(_pedido("ana@caracterizacion.test"), "completado")  # no explota


# --- Casos sin destino: no es un error -------------------------------------


@pytest.mark.parametrize(
    "direccion_envio",
    [None, "", "   ", "no soy json", "[1, 2, 3]", '"un string"', "{}", '{"email": ""}',
     '{"email": null}', '{"email": "   "}'],
)
def test_direccion_envio_invalida_no_rompe_nada(correo, direccion_envio):
    """Cualquier `direccion_envio` raro significa "no hay a quien mandar".

    La columna la arma el propio caso de uso con `json.dumps`, pero es texto
    crudo: nada impide que llegue vacia desde una fila vieja, desde la venta
    local o desde un import. Ninguno de esos casos puede tumbar un pago.
    """
    pedido = Pedido(usuario_id=uuid.uuid4(), direccion_envio=direccion_envio)

    _servicio(correo)._enviar_comprobante(pedido, "completado")

    assert correo.enviados == [], f"no deberia haberse enviado a {direccion_envio!r}"


def test_email_con_espacios_al_rededor_se_normaliza():
    """El cliente puede mandar ` " ana@x.test " ` y el destino es el mismo."""
    pedido = Pedido(
        usuario_id=uuid.uuid4(), direccion_envio=json.dumps({"email": "  ana@x.test  "})
    )

    assert _email_del_cliente(pedido.direccion_envio) == "ana@x.test"


# --- Best-effort: el correo no rompe el pago -------------------------------


def test_un_correo_que_falla_no_propaga_la_excepcion():
    """El pago esta confirmado: una excepcion de correo no puede deshacerlo."""
    servicio = _servicio(_CorreoFalso(falla=True))

    # No raises: si la excepcion escapara, `confirmar` devolvería 500 despues de
    # haber descontado el stock, y la pasarela reintentaria un pago ya cobrado.
    servicio._enviar_comprobante(_pedido("ana@caracterizacion.test"), "completado")


def test_el_fallo_del_correo_queda_logueado(caplog):
    """Un fallo silencioso es un fallo que se descubre cuando el cliente se queja."""
    servicio = _servicio(_CorreoFalso(falla=True))

    with caplog.at_level("ERROR"):
        servicio._enviar_comprobante(_pedido("ana@caracterizacion.test"), "completado")

    assert any(
        "comprobante" in registro.message.lower() for registro in caplog.records
    ), f"el fallo del correo no se logueo: {[r.message for r in caplog.records]}"


# --- El retorno: para que la pantalla de exito no prometa lo que no se sabe ---


def test_devuelve_true_cuando_el_correo_se_mando(correo):
    assert _servicio(correo)._enviar_comprobante(
        _pedido("ana@caracterizacion.test"), "completado"
    ) is True


def test_devuelve_false_cuando_el_correo_falla():
    """Un `except Exception` tragado sin.return valeria silenciosamente None.

    Eso hacia que la respuesta fuera indistinguible de "no hay correo
    configurado". El frontend necesita un booleano explicito para no decirle
    al cliente que le mandamos el comprobante cuando no se mando.
    """
    servicio = _servicio(_CorreoFalso(falla=True))

    assert servicio._enviar_comprobante(
        _pedido("ana@caracterizacion.test"), "completado"
    ) is False


def test_devuelve_false_sin_email_del_cliente(correo):
    pedido = _pedido(None)

    assert _servicio(correo)._enviar_comprobante(pedido, "completado") is False
    assert correo.enviados == []


def test_devuelve_false_sin_correo_configurado():
    """Sin servicio de correo el pago anda igual, pero no se puede prometer el mail."""
    servicio = ProcesarPago(
        pedidos=None,
        pagos=None,
        productos=None,
        pasarela=_PasarelaFalsa(),
        carritos=None,
    )

    assert servicio._enviar_comprobante(
        _pedido("ana@caracterizacion.test"), "completado"
    ) is False


