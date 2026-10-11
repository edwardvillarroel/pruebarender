from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class DetallePedido:
    pedido_id: UUID
    producto_id: UUID
    cantidad: int
    precio_unitario: int
    color: str | None = None
    nombre: str | None = None
    # Ruta pública del BLOB de la foto de la línea: la del color elegido si esa
    # variante tiene imagen, si no la del producto. La deriva el repositorio al
    # leer; queda en None si ni el producto ni el color guardan una foto.
    imagen: str | None = None
    id: UUID = field(default_factory=uuid4)