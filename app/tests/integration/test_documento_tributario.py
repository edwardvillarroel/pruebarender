"""El documento electrónico se emite cuando el pago se confirma, y queda.

Este test es el recorrido completo contra la base de verdad: entra por la API
pública (`POST /api/pago/crear` y `POST /api/pago/confirmar`) y sale por la
API pública (`GET /api/pedidos/<id>/documento` y su PDF).

Lo que se verifica:

- El pedido recuerda qué documento pidió el cliente (columna `tipo_documento`).
- Al confirmar el pago se emite el documento y se guarda su folio, su token y
  su PDF.
- Confirmar de nuevo NO emite un segundo documento (la idempotencia).
- El comprobante se puede volver a bajar aunque el proveedor se caiga: el PDF
  está en la base.

El proveedor de documentos es un doble: no sale nada a la red. Lo que se prueba
acá es la persistencia y el enganche con el pago, no el HTTP contra OpenFactura
(eso vive en `tools/verificar_openfactura.py` y en los tests unitarios del
cliente).
"""

from __future__ import annotations

import json
from datetime import date
from uuid import UUID

import pytest

from app.application.common.referencias import codificar_referencia
from app.application.facturacion.emitir_documento_tributario import (
    EmitirDocumentoTributario,
)
from app.application.pedidos_pagos.procesar_pago import ProcesarPago
from app.domain.interfaces.facturacion import (
    DocumentoConsultado,
    DocumentoEmitido,
    EmisorTributario,
)
from app.domain.interfaces.pasarela_pago import (
    PasarelaPago,
    ResultadoIntentoPago,
    SolicitudPago,
)
from app.infrastructure.repositories.carrito_repository_bd import CarritoRepositoryBd
from app.infrastructure.repositories.documento_tributario_repository import (
    DocumentoTributarioRepository,
)
from app.infrastructure.repositories.pago_repository import PagoRepository
from app.infrastructure.repositories.pedido_repository import PedidoRepository
from app.infrastructure.repositories.producto_repository import ProductoRepository

URL_FALSA = "https://pasarela-falsa.test/pagar"


class _PasarelaFalsa(PasarelaPago):
    def crear_intento(self, solicitud: SolicitudPago) -> ResultadoIntentoPago:
        return ResultadoIntentoPago(url=URL_FALSA, token=solicitud.referencia)

    def verificar_firma(self, parametros: dict[str, str]) -> bool:
        return True


class _EmisorFalso(EmisorTributario):
    """Proveedor de documentos que no sale a la red."""

    def __init__(self) -> None:
        self.llamadas: list = []

    @property
    def rut_emisor(self) -> str:
        return "76795561-8"

    def emitir(self, solicitud) -> DocumentoEmitido:
        self.llamadas.append(solicitud)
        return DocumentoEmitido(
            folio=712500,
            token="t" * 64,
            monto_neto=4202,
            iva=798,
            monto_total=solicitud.monto_total,
            fecha_emision=date(2026, 10, 22),
            pdf=b"%PDF-1.4 documento de prueba",
        )

    def consultar_documento(self, token: str) -> DocumentoConsultado:
        return DocumentoConsultado(folio=712500, pdf=b"%PDF-1.4 recuperado")


@pytest.fixture
def emisor():
    return _EmisorFalso()


@pytest.fixture
def pago_con_documentos(app, emisor):
    """`ProcesarPago` con el servicio de documentos conectado.

    Es el mismo cableado que hace `app/__init__.py`, pero con un emisor falso:
    la escritura del pedido, del pago y del documento sigue yendo a la base
    de verdad, que es lo que hay que probar.
    """
    servicio = ProcesarPago(
        PedidoRepository(),
        PagoRepository(),
        ProductoRepository(),
        _PasarelaFalsa(),
        CarritoRepositoryBd(),
        None,
        EmitirDocumentoTributario(
            PedidoRepository(), DocumentoTributarioRepository(), emisor
        ),
    )
    app.config["PAGO_SERVICE"] = servicio
    return servicio


def _cabeceras(usuario) -> dict:
    return {"X-User-Id": str(usuario.id), "X-User-Rol": "cliente"}


def _comprar(client, cabeceras, producto_id, cliente=None) -> dict:
    cuerpo = {
        "entrega": "retiro",
        "items": [{"id": str(producto_id), "cantidad": 1}],
    }
    if cliente:
        cuerpo["cliente"] = cliente
    creado = client.post("/api/pago/crear", json=cuerpo, headers=cabeceras)
    assert creado.status_code == 200, creado.get_json()
    listado = client.get("/api/pedidos", headers=cabeceras).get_json()["pedidos"]
    return listado[-1]


def _confirmar(client, pedido) -> dict:
    respuesta = client.post(
        "/api/pago/confirmar",
        json={
            "x_reference": codificar_referencia(UUID(pedido["id"])),
            "x_result": "completed",
        },
    )
    assert respuesta.status_code == 200, respuesta.get_json()
    return respuesta.get_json()


def test_el_pedido_guarda_el_tipo_de_documento_pedido(
    client, producto, usuario, centinela, pago_con_documentos
):
    p = producto(stock=10, nombre=f"{centinela}-llavero", precio=5000)
    cabeceras = _cabeceras(usuario)

    pedido = _comprar(
        client,
        cabeceras,
        p.id,
        {"tipoDocumento": "boleta", "rut": "12345678-5", "email": "a@b.cl"},
    )

    assert pedido["tipo_documento"] == "boleta", (
        f"el pedido no guardó el tipo de documento: {pedido!r}"
    )


def test_al_confirmar_el_pago_se_emite_el_documento(
    client, producto, usuario, centinela, pago_con_documentos, emisor
):
    p = producto(stock=10, nombre=f"{centinela}-llavero", precio=5000)
    cabeceras = _cabeceras(usuario)
    pedido = _comprar(
        client,
        cabeceras,
        p.id,
        {"tipoDocumento": "boleta", "rut": "12345678-5", "email": "a@b.cl"},
    )

    _confirmar(client, pedido)

    assert len(emisor.llamadas) == 1, "no se llamó al proveedor de documentos"
    assert emisor.llamadas[0].clave_idempotencia == f"dte-{pedido['id']}"
    assert emisor.llamadas[0].monto_total == pedido["total"]


def test_el_documento_emitted_se_consulta_por_la_api(
    client, producto, usuario, centinela, pago_con_documentos
):
    p = producto(stock=10, nombre=f"{centinela}-llavero", precio=5000)
    cabeceras = _cabeceras(usuario)
    pedido = _comprar(
        client,
        cabeceras,
        p.id,
        {"tipoDocumento": "boleta", "rut": "12345678-5", "email": "a@b.cl"},
    )
    _confirmar(client, pedido)

    respuesta = client.get(
        f"/api/pedidos/{pedido['id']}/documento", headers=cabeceras
    )

    assert respuesta.status_code == 200, respuesta.get_json()
    documento = respuesta.get_json()
    assert documento["folio"] == 712500
    assert documento["estado"] == "emitido"
    assert documento["tipo"] == "boleta"
    assert documento["rut_receptor"] == "12345678-5"
    assert documento["monto_total"] == pedido["total"]
    assert documento["tiene_pdf"] is True


def test_el_pdf_del_documento_se_baja(
    client, producto, usuario, centinela, pago_con_documentos
):
    p = producto(stock=10, nombre=f"{centinela}-llavero", precio=5000)
    cabeceras = _cabeceras(usuario)
    pedido = _comprar(
        client,
        cabeceras,
        p.id,
        {"tipoDocumento": "boleta", "rut": "12345678-5", "email": "a@b.cl"},
    )
    _confirmar(client, pedido)

    respuesta = client.get(
        f"/api/pedidos/{pedido['id']}/documento/pdf", headers=cabeceras
    )

    assert respuesta.status_code == 200
    assert respuesta.mimetype == "application/pdf"
    assert respuesta.data == b"%PDF-1.4 documento de prueba"


def test_confirmar_de_nuevo_no_emite_un_segundo_documento(
    client, producto, usuario, centinela, pago_con_documentos, emisor
):
    """La idempotencia es del negocio: un pedido, un documento.

    La pasarela reintenta el callback (hasta 10 veces si no recibe 200), así que
    el camino de "pago ya confirmado" se recorre muchas veces en la vida real.
    """
    p = producto(stock=10, nombre=f"{centinela}-llavero", precio=5000)
    cabeceras = _cabeceras(usuario)
    pedido = _comprar(
        client,
        cabeceras,
        p.id,
        {"tipoDocumento": "boleta", "rut": "12345678-5", "email": "a@b.cl"},
    )

    _confirmar(client, pedido)
    _confirmar(client, pedido)
    _confirmar(client, pedido)

    assert len(emisor.llamadas) == 1, (
        f"se llamó al proveedor {len(emisor.llamadas)} veces por el mismo pedido"
    )


def test_un_pedido_sin_rut_no_emite_documento(
    client, producto, usuario, centinela, pago_con_documentos, emisor
):
    """Sin RUT no hay comprobante: el pedido igual se paga igual."""
    p = producto(stock=10, nombre=f"{centinela}-llavero", precio=5000)
    cabeceras = _cabeceras(usuario)
    pedido = _comprar(
        client, cabeceras, p.id, {"tipoDocumento": "boleta", "email": "a@b.cl"}
    )

    _confirmar(client, pedido)

    assert emisor.llamadas == []
    respuesta = client.get(
        f"/api/pedidos/{pedido['id']}/documento", headers=cabeceras
    )
    assert respuesta.status_code == 404


def test_otro_usuario_no_ve_el_documento(
    client, producto, usuario, centinela, pago_con_documentos, db_sesion
):
    """El comprobante es del dueño del pedido: no se filtra a otros."""
    from app.infrastructure.database.models.usuario_model import UsuarioModel

    p = producto(stock=10, nombre=f"{centinela}-llavero", precio=5000)
    cabeceras = _cabeceras(usuario)
    pedido = _comprar(
        client,
        cabeceras,
        p.id,
        {"tipoDocumento": "boleta", "rut": "12345678-5", "email": "a@b.cl"},
    )
    _confirmar(client, pedido)

    otro = UsuarioModel(
        email=f"{centinela}-otro@caracterizacion.test",
        password_hash="r0-no-se-usa",
        nombre="R0 Caracterizacion",
        apellido="Otro",
    )
    db_sesion.add(otro)
    db_sesion.commit()

    respuesta = client.get(
        f"/api/pedidos/{pedido['id']}/documento",
        headers={"X-User-Id": str(otro.id), "X-User-Rol": "cliente"},
    )

    assert respuesta.status_code == 403
