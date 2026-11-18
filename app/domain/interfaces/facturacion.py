


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


    tipo: TipoDocumentoTributario
    clave_idempotencia: str
    receptor: DatosFacturacion
    lineas: list[LineaDocumento]
    monto_total: int
    medio_pago: MedioPagoFacturacion = MedioPagoFacturacion.TARJETA
    fecha_emision: date = field(default_factory=date.today)


@dataclass
class DocumentoEmitido:

    folio: int
    token: str
    monto_neto: int
    iva: int
    monto_total: int
    fecha_emision: date
    pdf: bytes | None = None


@dataclass
class DocumentoConsultado:

    folio: int
    pdf: bytes | None = None


class ErrorEmisionTributaria(Exception):


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

    @property
    @abstractmethod
    def rut_emisor(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def emitir(self, solicitud: SolicitudDocumentoTributario) -> DocumentoEmitido:
        raise NotImplementedError

    @abstractmethod
    def consultar_documento(self, token: str) -> DocumentoConsultado:

        raise NotImplementedError


class ServicioDocumentacionTributaria(ABC):


    @abstractmethod
    def emitir_para_pedido(self, pedido_id: UUID) -> DocumentoTributario | None:

        raise NotImplementedError
