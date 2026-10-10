from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.enums import EstadoSolicitudDiseno, TipoMaterial
from app.domain.time import utcnow


@dataclass
class SolicitudDiseno:
    usuario_id: UUID
    nombre: str
    email: str
    telefono: str | None
    material: TipoMaterial
    descripcion: str
    estado: EstadoSolicitudDiseno = EstadoSolicitudDiseno.PENDIENTE
    imagen: str | None = None
    modelo_url: str | None = None
    precio: int | None = None
    id: UUID = field(default_factory=uuid4)
    creado_en: datetime = field(default_factory=utcnow)
