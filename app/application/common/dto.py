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
    material: str | None = None
    tamano: str | None = None
    color: str | None = None
    specs: list[str] | None = None
    descuento: int | None = None


@dataclass
class ActualizarProductoDTO:
    id: UUID
    nombre: str | None = None
    categoria_id: UUID | None = None
    precio: int | None = None
    stock: int | None = None
    descripcion: str | None = None
    activo: bool | None = None
    material: str | None = None
    tamano: str | None = None
    color: str | None = None
    specs: list[str] | None = None
    descuento: int | None = None


@dataclass
class CrearCategoriaDTO:
    nombre: str
    descripcion: str | None = None


@dataclass
class ItemPedidoDTO:
    producto_id: UUID
    cantidad: int


@dataclass
class CrearPedidoDTO:
    usuario_id: UUID
    items: list[ItemPedidoDTO]
    entrega: str = "retiro"
    cliente: dict | None = None


@dataclass
class IniciarPagoDTO:
    usuario_id: UUID
    items: list[ItemPedidoDTO]
    entrega: str = "retiro"
    cliente: dict | None = None


@dataclass
class ResultadoConfirmacionPago:
    estado: str
    pedido_id: str
    mensaje: str
