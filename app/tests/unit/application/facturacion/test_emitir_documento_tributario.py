"""El caso de uso de emisión: una fila por pedido, un documento por venta.

Lo que se prueba acá es el CYCLE DE VIDA, que es donde está el riesgo real:

- La clave de idempotencia sale del id del pedido, así que siempre es la
  misma y el proveedor nunca emite dos veces la misma venta.
- Si el documento ya está emitido, no se vuelve a llamar al proveedor.
- Si el proveedor dice "ya lo emití" (`OF-06`), el documento se RECUPERA en
  vez de darse por fallido: el pago fue y el comprobante existe.
- Si el proveedor falla de verdad, el documento queda en estado `error` con el
  motivo, y el error sube: el pago no se reverse por un problema de
  facturación.

Los dobles son de memoria: no tocan la base ni la red.
"""

from __future__ import annotations

import json
from datetime import date
from uuid import UUID, uuid4

import pytest

from app.application.facturacion.emitir_documento_tributario import (
    EmitirDocumentoTributario,
)
from app.domain.entities.detalle_pedido import DetallePedido
from app.domain.entities.documento_tributario import DocumentoTributario
from app.domain.entities.pedido import Pedido
from app.domain.enums import EstadoDocumentoTributario, TipoDocumentoTributario
from app.domain.interfaces.facturacion import (
    DocumentoConsultado,
    DocumentoEmitido,
    ErrorEmisionTributaria,
)


# --------------------------------------------------------------------------
# Dobles
# --------------------------------------------------------------------------


class PedidosEnMemoria:
    def __init__(self, pedido: Pedido | None = None) -> None:
        self._pedido = pedido

    def get_by_id(self, pedido_id: UUID) -> Pedido | None:
        if self._pedido is None or self._pedido.id != pedido_id:
            return None
        return self._pedido


class DocumentosEnMemoria:
    def __init__(self) -> None:
        self.por_clave: dict[str, DocumentoTributario] = {}

    def get_by_clave_idempotencia(self, clave: str) -> DocumentoTributario | None:
        return self.por_clave.get(clave)

    def get_by_pedido(self, pedido_id: UUID) -> DocumentoTributario | None:
        for documento in self.por_clave.values():
            if documento.pedido_id == pedido_id:
                return documento
        return None

    def add(self, entidad: DocumentoTributario) -> DocumentoTributario:
        self.por_clave[entidad.clave_idempotencia] = entidad
        return entidad

    def update(self, entidad: DocumentoTributario) -> DocumentoTributario:
        self.por_clave[entidad.clave_idempotencia] = entidad
        return entidad


class EmisorFalso:
    def __init__(self, folio: int = 712500, error: Exception | None = None) -> None:
        self.folio = folio
        self.error = error
        self.llamadas: list = []
        self.consultas: list[str] = []

    @property
    def rut_emisor(self) -> str:
        return "76795561-8"

    def emitir(self, solicitud):
        self.llamadas.append(solicitud)
        if self.error is not None:
            raise self.error
        return DocumentoEmitido(
            folio=self.folio,
            token="t" * 64,
            monto_neto=840,
            iva=160,
            monto_total=solicitud.monto_total,
            fecha_emision=date(2026, 10, 22),
            pdf=b"%PDF-1.4",
        )

    def consultar_documento(self, token: str) -> DocumentoConsultado:
        self.consultas.append(token)
        return DocumentoConsultado(folio=self.folio, pdf=b"%PDF-1.4 recuperado")


def _pedido(cliente: dict, total: int = 1000, entrega: str = "retiro") -> Pedido:
    pedido = Pedido(
        usuario_id=uuid4(),
        direccion_envio=json.dumps(cliente, ensure_ascii=False),
        entrega=entrega,
        tipo_documento=TipoDocumentoTributario.BOLETA,
        total=total,
    )
    pedido.detalles = [
        DetallePedido(
            pedido_id=pedido.id,
            producto_id=uuid4(),
            cantidad=1,
            precio_unitario=total,
            nombre="Llavero 3D",
        )
    ]
    return pedido


def _servicio(pedido: Pedido | None = None, emisor: EmisorFalso | None = None):
    documentos = DocumentosEnMemoria()
    emisor = emisor or EmisorFalso()
    servicio = EmitirDocumentoTributario(
        PedidosEnMemoria(pedido), documentos, emisor
    )
    return servicio, documentos, emisor


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------


def test_emite_el_documento_del_pedido():
    pedido = _pedido({"tipoDocumento": "boleta", "rut": "12345678-5"})
    servicio, documentos, emisor = _servicio(pedido)

    documento = servicio.emitir_para_pedido(pedido.id)

    assert documento is not None
    assert documento.estado is EstadoDocumentoTributario.EMITIDO
    assert documento.folio == 712500
    assert documento.token == "t" * 64
    assert documento.monto_total == 1000
    assert documento.rut_emisor == "76795561-8"
    assert documento.rut_receptor == "12345678-5"
    assert documento.pdf == b"%PDF-1.4"
    assert len(emisor.llamadas) == 1


def test_la_clave_de_idempotencia_sale_del_pedido():
    """La misma venta tiene que producir la misma clave, siempre."""
    pedido = _pedido({"tipoDocumento": "boleta", "rut": "12345678-5"})
    servicio, _, emisor = _servicio(pedido)

    servicio.emitir_para_pedido(pedido.id)

    assert emisor.llamadas[0].clave_idempotencia == f"dte-{pedido.id}"


def test_no_emite_dos_veces_el_mismo_pedido():
    pedido = _pedido({"tipoDocumento": "boleta", "rut": "12345678-5"})
    servicio, _, emisor = _servicio(pedido)

    primero = servicio.emitir_para_pedido(pedido.id)
    segundo = servicio.emitir_para_pedido(pedido.id)

    assert primero.folio == segundo.folio
    assert len(emisor.llamadas) == 1, "se llamó al proveedor dos veces"


def test_sin_rut_no_emite_nada():
    """Sin RUT no hay documento: se devuelve `None` y no se toca el proveedor."""
    pedido = _pedido({"tipoDocumento": "boleta"})
    servicio, _, emisor = _servicio(pedido)

    assert servicio.emitir_para_pedido(pedido.id) is None
    assert emisor.llamadas == []


def test_sin_tipo_de_documento_no_emite_nada():
    pedido = _pedido({"rut": "12345678-5"})
    pedido.tipo_documento = None
    servicio, _, emisor = _servicio(pedido)

    assert servicio.emitir_para_pedido(pedido.id) is None
    assert emisor.llamadas == []


def test_una_factura_sin_los_datos_que_exige_el_sii_no_se_emite():
    """La factura exige razón social, giro, dirección y comuna.

    No es un detalle del formulario: sin ellos el SII rechaza el documento.
    """
    pedido = _pedido({"tipoDocumento": "factura", "rut": "12345678-5"})
    pedido.tipo_documento = TipoDocumentoTributario.FACTURA
    servicio, _, emisor = _servicio(pedido)

    with pytest.raises(ErrorEmisionTributaria) as excepcion:
        servicio.emitir_para_pedido(pedido.id)

    assert "razón social" in str(excepcion.value)
    assert emisor.llamadas == []


def test_una_factura_completa_se_emite():
    pedido = _pedido(
        {
            "tipoDocumento": "factura",
            "rut": "12345678-5",
            "razonSocial": "CLIENTE LTDA",
            "giro": "COMERCIO",
            "direccion": "AV. ALTA 123",
            "numero": "45",
            "comuna": "Providencia",
        }
    )
    pedido.tipo_documento = TipoDocumentoTributario.FACTURA
    servicio, _, emisor = _servicio(pedido)

    documento = servicio.emitir_para_pedido(pedido.id)

    assert documento.estado is EstadoDocumentoTributario.EMITIDO
    assert documento.razon_social_receptor == "CLIENTE LTDA"
    assert documento.direccion_receptor == "AV. ALTA 123 45"
    assert emisor.llamadas[0].tipo is TipoDocumentoTributario.FACTURA


def test_cuando_el_proveedor_dice_ya_emitido_se_recupera_el_documento():
    """`OF-06` con token: el documento existe, no hay que darlo por fallido."""
    error = ErrorEmisionTributaria(
        "Este DTE ya fue emitido", codigo="OF-06", token="z" * 64, ya_emitido=True
    )
    pedido = _pedido({"tipoDocumento": "boleta", "rut": "12345678-5"})
    servicio, _, emisor = _servicio(pedido, EmisorFalso(error=error))

    documento = servicio.emitir_para_pedido(pedido.id)

    assert documento.estado is EstadoDocumentoTributario.EMITIDO
    assert documento.token == "z" * 64
    assert documento.folio == 712500
    assert emisor.consultas == ["z" * 64]


def test_cuando_el_proveedor_falla_el_documento_queda_en_error():
    error = ErrorEmisionTributaria("Datos inválidos", codigo="OF-01")
    pedido = _pedido({"tipoDocumento": "boleta", "rut": "12345678-5"})
    servicio, documentos, _ = _servicio(pedido, EmisorFalso(error=error))

    with pytest.raises(ErrorEmisionTributaria):
        servicio.emitir_para_pedido(pedido.id)

    documento = documentos.get_by_pedido(pedido.id)
    assert documento.estado is EstadoDocumentoTributario.ERROR
    assert "OF-01" in documento.error


def test_reintenta_una_emision_que_habia_fallado():
    """Un documento en error se vuelve a pedir: el pago sigue en pie."""
    pedido = _pedido({"tipoDocumento": "boleta", "rut": "12345678-5"})
    documentos = DocumentosEnMemoria()
    emisor = EmisorFalso(
        error=ErrorEmisionTributaria("Datos inválidos", codigo="OF-01")
    )
    servicio = EmitirDocumentoTributario(PedidosEnMemoria(pedido), documentos, emisor)

    with pytest.raises(ErrorEmisionTributaria):
        servicio.emitir_para_pedido(pedido.id)

    emisor.error = None
    documento = servicio.emitir_para_pedido(pedido.id)

    assert documento.estado is EstadoDocumentoTributario.EMITIDO
    assert documento.error is None


def test_el_envio_cobrado_va_como_una_linea_mas():
    """Las líneas del documento tienen que sumar el total cobrado.

    El costo de envío se cobra aparte del precio de los productos: si no
    fuera una línea, el comprobante no cuadraría con el cobro.
    """
    pedido = _pedido(
        {"tipoDocumento": "boleta", "rut": "12345678-5"}, total=1000, entrega="envio"
    )
    pedido.total = 1000 + 5990
    servicio, _, emisor = _servicio(pedido)

    servicio.emitir_para_pedido(pedido.id)

    lineas = emisor.llamadas[0].lineas
    assert len(lineas) == 2
    assert lineas[-1].nombre == "Envío"
    assert lineas[-1].precio_unitario == 5990
    assert sum(linea.monto_bruto for linea in lineas) == pedido.total


def test_retiro_no_agrega_linea_de_envio():
    pedido = _pedido({"tipoDocumento": "boleta", "rut": "12345678-5"}, entrega="retiro")
    servicio, _, emisor = _servicio(pedido)

    servicio.emitir_para_pedido(pedido.id)

    assert len(emisor.llamadas[0].lineas) == 1


def test_un_pedido_inexistente_no_emite_nada():
    servicio, _, emisor = _servicio(None)

    assert servicio.emitir_para_pedido(uuid4()) is None
    assert emisor.llamadas == []
