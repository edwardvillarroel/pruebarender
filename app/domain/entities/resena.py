from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.time import utcnow


@dataclass
class Resena:
    """Reseña inmutable de un producto dentro de un pedido (1-5 estrellas).

    La unicidad es el triple `(usuario_id, pedido_id, producto_id)`: el mismo
    producto se reseña una sola vez por pedido, sin edición ni borrado en v1.
    `estrellas` es entero 1-5; la validación vive en el caso de uso y el
    CHECK de la tabla es la red de seguridad.
    """

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
    """Vista publica de una resena: sin `usuario_id`, con nombre para mostrar."""

    id: UUID
    producto_id: UUID
    estrellas: int
    comentario: str | None
    creado_en: datetime
    autor: str
