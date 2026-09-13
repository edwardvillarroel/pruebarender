from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class ItemCarrito:
    """Línea del carrito: referencia a un producto y su cantidad.

    `id` es el identificador del ítem dentro del carrito (UUID generado por
    el backend). `producto_id` es el identificador del producto del catálogo
    (por ahora texto, ya que el catálogo sigue siendo mock).
    """

    producto_id: str
    cantidad: int
    id: UUID = field(default_factory=uuid4)
    agregado_en: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Carrito:
    """Carrito de compras de un usuario/sesión.

    `usuario_id` llega como parámetro explícito desde la capa de API; en la
    fase de autenticación será el `sub` del JWT.
    """

    usuario_id: str
    items: list[ItemCarrito] = field(default_factory=list)
    actualizado_en: datetime = field(default_factory=datetime.utcnow)