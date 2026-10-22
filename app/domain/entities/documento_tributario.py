from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4

from app.domain.enums import EstadoDocumentoTributario, TipoDocumentoTributario
from app.domain.time import utcnow


@dataclass
class DatosFacturacion:
    """Datos del receptor del documento tributario.

    Son los que el cliente cautó en el checkout (`tipoDocumento`, `rut`,
    `razonSocial`, `giro`, dirección y comuna). Para una boleta basta el RUT:
    el SII no exige razón social ni giro. Para una factura (DTE 33) sí.
    """

    tipo: TipoDocumentoTributario
    rut: str
    razon_social: str | None = None
    giro: str | None = None
    direccion: str | None = None
    comuna: str | None = None
    email: str | None = None


@dataclass
class LineaDocumento:
    """Una línea del documento: producto, cantidad y precio unitario.

    El precio es BRUTO (IVA incluido), que es como están los precios en el
    catálogo. El desglose a neto e IVA lo hace el cálculo fiscal según el
    tipo de documento.
    """

    nombre: str
    cantidad: int
    precio_unitario: int

    @property
    def monto_bruto(self) -> int:
        return self.precio_unitario * self.cantidad


@dataclass
class DocumentoTributario:
    """Un documento electrónico emitido (o en proceso de emitirse).

    Es el registro de lo que se emitió: guarda el folio del SII, el token del
    proveedor y el PDF, de modo que el comprobante se pueda volver a entregar
    aunque el proveedor deje de servirlo.
    """

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
