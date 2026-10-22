"""Contratos de la facturación electrónica (DTE).

Hay dos puertos y son de distinta naturaleza:

- `EmisorTributario` es el PROVEEDOR (OpenFactura, de Haulmer). La aplicación
  solo conoce este contrato; el cliente HTTP vive en `infrastructure`.
- `ServicioDocumentacionTributaria` es el CASO DE USO de emisión. Existe como
  puerto para que `ProcesarPago` (que vive en otro módulo de `application`)
  lo use sin importar ese módulo: los módulos de `application` no se importan
  entre sí.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from app.domain.entities.documento_tributario import (
    DatosFacturacion,
    DocumentoTributario,
    LineaDocumento,
)
from app.domain.enums import MedioPagoFacturacion, TipoDocumentoTributario


@dataclass
class SolicitudDocumentoTributario:
    """Lo que hay que emitir.

    Los montos van BRUTOS (IVA incluido), igual que los precios del catálogo.
    El desglose a neto e IVA depende del tipo de documento y lo hace el
    cálculo fiscal, no quien arma la solicitud.
    """

    tipo: TipoDocumentoTributario
    clave_idempotencia: str
    receptor: DatosFacturacion
    lineas: list[LineaDocumento]
    monto_total: int
    medio_pago: MedioPagoFacturacion = MedioPagoFacturacion.TARJETA
    fecha_emision: date = field(default_factory=date.today)


@dataclass
class DocumentoEmitido:
    """Lo que devolvió el proveedor al emitir."""

    folio: int
    token: str
    monto_neto: int
    iva: int
    monto_total: int
    fecha_emision: date
    pdf: bytes | None = None


@dataclass
class DocumentoConsultado:
    """Datos de un documento que ya fue emitido, recovered por su token."""

    folio: int
    pdf: bytes | None = None


class ErrorEmisionTributaria(Exception):
    """El proveedor no pudo emitir el documento.

    `token` se llena cuando el proveedor responde que el documento YA fue
    emitido con esa clave de idempotencia: en ese caso el token es el del
    documento emitido y el caso de uso puede recuperarlo en vez de fallar.
    """

    def __init__(
        self,
        mensaje: str,
        codigo: str | None = None,
        token: str | None = None,
        ya_emitido: bool = False,
    ) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.token = token
        self.ya_emitido = ya_emitido


class EmisorTributario(ABC):
    """Contrato del proveedor que emite los documentos electrónicos."""

    @property
    @abstractmethod
    def rut_emisor(self) -> str:
        """RUT de la organización que emite (la certificada ante el SII)."""
        raise NotImplementedError

    @abstractmethod
    def emitir(self, solicitud: SolicitudDocumentoTributario) -> DocumentoEmitido:
        """Emite el documento y devuelve el folio y el token."""
        raise NotImplementedError

    @abstractmethod
    def consultar_documento(self, token: str) -> DocumentoConsultado:
        """Recupera un documento ya emitido (folio y PDF) por su token.

        Es la vía de salida cuando el proveedor responde que el documento ya
        existía: el token viene en el error y con él se recupera el PDF.
        """
        raise NotImplementedError


class ServicioDocumentacionTributaria(ABC):
    """Caso de uso de emisión, visto desde afuera.

    Quien lo consume (por ejemplo `ProcesarPago`) solo necesita pedir la
    emisión de un pedido y saber si terminó bien.
    """

    @abstractmethod
    def emitir_para_pedido(self, pedido_id: UUID) -> DocumentoTributario | None:
        """Emite el documento del pedido.

        Devuelve `None` si el pedido no pide documento (por ejemplo, una venta
        local, que se emite por su propia vía). Lanza `ErrorEmisionTributaria`
        si el proveedor falla.
        """
        raise NotImplementedError
