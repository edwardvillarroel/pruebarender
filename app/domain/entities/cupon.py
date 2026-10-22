from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.time import utcnow


@dataclass
class Cupon:
    codigo: str
    tipo: str = "porcentaje"
    valor: float = 0
    activo: bool = True
    uso_unico: bool = False
    usado: bool = False
    usado_por: UUID | None = None
    usado_en: datetime | None = None
    creado_por: UUID | None = None
    descripcion: str | None = None
    id: UUID = field(default_factory=uuid4)
    creado_en: datetime = field(default_factory=utcnow)
