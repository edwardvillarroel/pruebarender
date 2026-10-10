from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.enums import EstadoPago
from app.domain.time import utcnow


@dataclass
class Pago:
    pedido_id: UUID
    monto: int
    proveedor: str
    estado: EstadoPago = EstadoPago.PENDIENTE
    token: str | None = None
    clave_idempotencia: str | None = None
    url_intento: str | None = None
    id: UUID = field(default_factory=uuid4)
    creado_en: datetime = field(default_factory=utcnow)
