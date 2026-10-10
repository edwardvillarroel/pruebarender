
from dataclasses import dataclass, field
from datetime import datetime
from app.domain.time import utcnow


@dataclass
class EventoSeguimiento:
    fecha: datetime | None = None
    descripcion: str | None = None
    sucursal: str | None = None
    ciudad: str | None = None
    estado: str | None = None


@dataclass
class SeguimientoStarken:
    codigo: str
    estado: str | None = None
    descripcion: str | None = None
    historial: list[EventoSeguimiento] = field(default_factory=list)
    consultado_en: datetime = field(default_factory=utcnow)
