from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from app.domain.time import utcnow


@dataclass
class LogAuditoria:
    accion: str
    entidad_tipo: str
    entidad_id: str | None
    usuario_id: UUID | None
    detalle: str | None = None
    ip: str | None = None
    id: UUID = field(default_factory=uuid4)
    creado_en: datetime = field(default_factory=utcnow)
