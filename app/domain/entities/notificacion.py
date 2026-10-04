from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from app.domain.time import utcnow


@dataclass
class Notificacion:
    usuario_id: UUID
    tipo: str
    asunto: str
    contenido: str
    canal: str = "email"
    leida: bool = False
    id: UUID = field(default_factory=uuid4)
    creado_en: datetime = field(default_factory=utcnow)
