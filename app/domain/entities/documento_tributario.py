from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4

from app.domain.enums import EstadoDocumentoTributario, TipoDocumentoTributario
from app.domain.time import utcnow


@dataclass
class DatosFacturacion:


    tipo: TipoDocumentoTributario
    rut: str
    razon_social: str | None = None
    giro: str | None = None
    direccion: str | None = None
    comuna: str | None = None
    email: str | None = None


@dataclass
class LineaDocumento:


    nombre: str
    cantidad: int
    precio_unitario: int

    @property
    def monto_bruto(self) -> int:
        return self.precio_unitario * self.cantidad


@dataclass
class DocumentoTributario:


    tipo: TipoDocumentoTributario
    clave_idempotencia: str
    rut_emisor: str
    rut_receptor: str
    monto_neto: int = 0
    iva: int = 0
    monto_total: int = 0
    estado: EstadoDocumentoTributario = EstadoDocumentoTributario.PENDIENTE
    pedido_id: UUID | None = None
    folio: int | None = None
    token: str | None = None
    razon_social_receptor: str | None = None
    giro_receptor: str | None = None
    direccion_receptor: str | None = None
    comuna_receptor: str | None = None
    fecha_emision: date | None = None
    error: str | None = None
    pdf: bytes | None = None
    id: UUID = field(default_factory=uuid4)
    creado_en: datetime = field(default_factory=utcnow)
