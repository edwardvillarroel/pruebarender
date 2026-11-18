





from __future__ import annotations

import json
import uuid

import pytest

from app.application.pedidos_pagos.procesar_pago import (
    ProcesarPago,
    _email_del_cliente,
)
from app.domain.entities.pedido import Pedido
from app.domain.entities.producto import Producto
from app.domain.interfaces.pasarela_pago import PasarelaPago


class _PasarelaFalsa(PasarelaPago):
    def crear_intento(self, solicitud):  # pragma: no cover - no se usa aca
        raise AssertionError("no se deberia abrir un intento en estos tests")

    def verificar_firma(self, parametros: dict[str, str]) -> bool:
        return True


class _CorreoFalso:

    def __init__(self, falla: bool = False):
        self.enviados: list[tuple[Pedido, str, str]] = []
        self.admin_pedidos: list[tuple[Pedido, str, str]] = []
        self.admin_stock: list[list[Producto]] = []
        self._falla = falla

    def enviar_comprobante_pedido(
        self, pedido: Pedido, cliente_email: str, estado_pago: str
    ) -> None:
        if self._falla:
            raise RuntimeError("Resend devolvio 500")
        self.enviados.append((pedido, cliente_email, estado_pago))

    def avisar_admin_pedido_pagado(
        self, pedido: Pedido, cliente_email: str, estado_pago: str
    ) -> None:
        if self._falla:
            raise RuntimeError("Resend devolvio 500")
        self.admin_pedidos.append((pedido, cliente_email, estado_pago))

    def avisar_admin_stock_bajo(self, productos: list[Producto]) -> None:
        if self._falla:
            raise RuntimeError("Resend devolvio 500")
        self.admin_stock.append(list(productos))

    def avisar_admin_nueva_cotizacion(self, solicitud) -> None:  # pragma: no cover
        raise AssertionError("no se usa en estos tests")

    def enviar_estado_cotizacion(self, solicitud, estado, precio=None):  # pragma: no cover
        raise AssertionError("no se usa en estos tests")


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

    return ProcesarPago(
        pedidos=None,
        pagos=None,
        productos=None,
        pasarela=_PasarelaFalsa(),
        carritos=None,
        correo=correo,
    )




def test_envia_el_comprobante_al_email_del_cliente(correo):
    _servicio(correo)._enviar_comprobante(_pedido("ana@caracterizacion.test"), "completado")

    assert len(correo.enviados) == 1, "no se envio ningun comprobante"
    pedido, email, _ = correo.enviados[0]
    assert email == "ana@caracterizacion.test"


def test_el_comprobante_lleva_el_estado_del_pago_no_el_del_pedido(correo):

    _servicio(correo)._enviar_comprobante(_pedido("ana@caracterizacion.test"), "completado")

    pedido, _, estado_pago = correo.enviados[0]
    assert pedido.estado.value == "pendiente", "el pedido sale pendiente, por diseño"
    assert estado_pago == "completado", "pero el comprobante debe reportar el pago"


def test_sin_correo_configurado_no_intenta_nada():

    servicio = ProcesarPago(
        pedidos=None,
        pagos=None,
        productos=None,
        pasarela=_PasarelaFalsa(),
        carritos=None,
    )

    servicio._enviar_comprobante(_pedido("ana@caracterizacion.test"), "completado")




@pytest.mark.parametrize(
    "direccion_envio",
    [None, "", "   ", "no soy json", "[1, 2, 3]", '"un string"', "{}", '{"email": ""}',
     '{"email": null}', '{"email": "   "}'],
)
def test_direccion_envio_invalida_no_rompe_nada(correo, direccion_envio):

    pedido = Pedido(usuario_id=uuid.uuid4(), direccion_envio=direccion_envio)

    _servicio(correo)._enviar_comprobante(pedido, "completado")

    assert correo.enviados == [], f"no deberia haberse enviado a {direccion_envio!r}"


def test_email_con_espacios_al_rededor_se_normaliza():
    pedido = Pedido(
        usuario_id=uuid.uuid4(), direccion_envio=json.dumps({"email": "  ana@x.test  "})
    )

    assert _email_del_cliente(pedido.direccion_envio) == "ana@x.test"




def test_un_correo_que_falla_no_propaga_la_excepcion():
    servicio = _servicio(_CorreoFalso(falla=True))

    servicio._enviar_comprobante(_pedido("ana@caracterizacion.test"), "completado")


def test_el_fallo_del_correo_queda_logueado(caplog):
    servicio = _servicio(_CorreoFalso(falla=True))

    with caplog.at_level("ERROR"):
        servicio._enviar_comprobante(_pedido("ana@caracterizacion.test"), "completado")

    assert any(
        "comprobante" in registro.message.lower() for registro in caplog.records
    ), f"el fallo del correo no se logueo: {[r.message for r in caplog.records]}"




def test_devuelve_true_cuando_el_correo_se_mando(correo):
    assert _servicio(correo)._enviar_comprobante(
        _pedido("ana@caracterizacion.test"), "completado"
    ) is True


def test_devuelve_false_cuando_el_correo_falla():

    servicio = _servicio(_CorreoFalso(falla=True))

    assert servicio._enviar_comprobante(
        _pedido("ana@caracterizacion.test"), "completado"
    ) is False


def test_devuelve_false_sin_email_del_cliente(correo):
    pedido = _pedido(None)

    assert _servicio(correo)._enviar_comprobante(pedido, "completado") is False
    assert correo.enviados == []


def test_devuelve_false_sin_correo_configurado():
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




def _producto(stock: int = 0) -> Producto:
    return Producto(
        nombre="Llavero",
        categoria_id=uuid.uuid4(),
        precio=1000,
        stock=stock,
        stock_minimo=3,
    )


class _ProductosFalsos:
    def __init__(self, pendientes=None, falla: bool = False):
        self.pendientes = pendientes or []
        self.falla = falla
        self.consultados: list = []
        self.marcados: list = []

    def listar_avisos_stock_pendientes(self, ids):
        if self.falla:
            raise RuntimeError("la base se cayo")
        self.consultados = list(ids)
        return self.pendientes

    def marcar_aviso_stock_notificado(self, ids):
        self.marcados = list(ids)


def test_avisa_al_admin_del_pedido_pagado(correo):
    _servicio(correo)._avisar_admin_pedido(
        _pedido("ana@caracterizacion.test"),
        "ana@caracterizacion.test",
        "completado",
    )

    assert len(correo.admin_pedidos) == 1
    _, email, estado_pago = correo.admin_pedidos[0]
    assert email == "ana@caracterizacion.test"
    assert estado_pago == "completado"


def test_el_aviso_al_admin_no_rompe_el_pago_si_falla():
    servicio = _servicio(_CorreoFalso(falla=True))

    servicio._avisar_admin_pedido(
        _pedido("ana@caracterizacion.test"),
        "ana@caracterizacion.test",
        "completado",
    )


def test_avisa_al_admin_del_stock_y_marca_los_productos(correo):
    producto = _producto()
    productos = _ProductosFalsos(pendientes=[producto])
    servicio = ProcesarPago(
        pedidos=None,
        pagos=None,
        productos=productos,
        pasarela=_PasarelaFalsa(),
        carritos=None,
        correo=correo,
    )

    servicio._avisar_admin_stock([producto.id])

    assert correo.admin_stock == [[producto]]
    assert productos.marcados == [producto.id]


def test_si_falla_el_aviso_de_stock_no_se_marca_como_notificado():
    producto = _producto()
    productos = _ProductosFalsos(pendientes=[producto])
    servicio = ProcesarPago(
        pedidos=None,
        pagos=None,
        productos=productos,
        pasarela=_PasarelaFalsa(),
        carritos=None,
        correo=_CorreoFalso(falla=True),
    )

    servicio._avisar_admin_stock([producto.id])

    assert productos.marcados == [], "un aviso fallido no puede darse por enviado"


def test_si_la_consulta_de_stock_falla_el_pago_sigue():
    producto = _producto()
    productos = _ProductosFalsos(falla=True)
    servicio = ProcesarPago(
        pedidos=None,
        pagos=None,
        productos=productos,
        pasarela=_PasarelaFalsa(),
        carritos=None,
        correo=_CorreoFalso(),
    )

    servicio._avisar_admin_stock([producto.id])


def test_sin_correo_no_consulta_stock():
    class _ProductosQueNoSeTocan:
        def listar_avisos_stock_pendientes(self, ids):  # pragma: no cover
            raise AssertionError("sin correo no hay aviso que preparar")

    servicio = ProcesarPago(
        pedidos=None,
        pagos=None,
        productos=_ProductosQueNoSeTocan(),
        pasarela=_PasarelaFalsa(),
        carritos=None,
    )

    servicio._avisar_admin_stock([uuid.uuid4()])


