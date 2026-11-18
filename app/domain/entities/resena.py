from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.time import utcnow


@dataclass
class Resena:


    usuario_id: UUID
    pedido_id: UUID
    producto_id: UUID
    estrellas: int
    comentario: str | None = None
    id: UUID = field(default_factory=uuid4)
    creado_en: datetime = field(default_factory=utcnow)
    actualizado_en: datetime | None = None


@dataclass
class ResenaPublica:

    id: UUID
    producto_id: UUID
    estrellas: int
    comentario: str | None
    creado_en: datetime
    autor: str
