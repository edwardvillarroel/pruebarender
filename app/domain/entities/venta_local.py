from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4

from app.domain.enums import EstadoSesionVenta, MedioPago


@dataclass
class SesionVenta:
    lugar: str
    fecha: date
    usuario_id: UUID
    estado: str = EstadoSesionVenta.ABIERTA.value
    creado_en: datetime | None = None
    cerrada_en: datetime | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass
class VentaLocalItem:
    producto_id: UUID
    nombre: str
    cantidad: int
    precio_unitario: int
    venta_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass
class VentaLocal:
    sesion_id: UUID
    medio_pago: str
    items: list[VentaLocalItem]
    total: int = 0
    creado_en: datetime | None = None
    id: UUID = field(default_factory=uuid4)