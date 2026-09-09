from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class CrearProductoDTO:
    nombre: str
    categoria_id: UUID
    precio: int
    stock: int = 0
    descripcion: str | None = None
    imagen: str | None = None


@dataclass
class ActualizarProductoDTO:
    nombre: str | None = None
    precio: int | None = None
    stock: int | None = None
    descripcion: str | None = None
    activo: bool | None = None
    id: UUID | None = field(default=None)


@dataclass
class CrearCategoriaDTO:
    nombre: str
    descripcion: str | None = None