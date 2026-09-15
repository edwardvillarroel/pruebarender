import math
from typing import Any
from uuid import UUID

from app.application.common.dto import ActualizarProductoDTO, CrearProductoDTO
from app.domain.entities.producto import ImagenProducto, Producto
from app.domain.interfaces.repositories import ProductoRepository


def _calcular_precio_original(precio: int, descuento: int) -> int:
    """Calcula el precio original a partir del precio con descuento."""
    if descuento <= 0 or descuento >= 100:
        return precio
    return math.ceil(precio / (1 - descuento / 100))


class GestionarProducto:
    """Caso de uso: CRUD de productos del catálogo."""

    def __init__(self, repositorio: ProductoRepository) -> None:
        self._repositorio = repositorio

    def crear(self, dto: CrearProductoDTO) -> Producto:
        precio_original = None
        if dto.descuento and dto.descuento > 0:
            precio_original = _calcular_precio_original(dto.precio, dto.descuento)
        producto = Producto(
            nombre=dto.nombre,
            categoria_id=dto.categoria_id,
            precio=dto.precio,
            stock=dto.stock,
            descripcion=dto.descripcion,
            imagen=dto.imagen,
            material=dto.material,
            tamano=dto.tamano,
            color=dto.color,
            specs=dto.specs,
            descuento=dto.descuento,
            precio_original=precio_original,
        )
        return self._repositorio.add(producto)

    def consultar(self, producto_id: UUID) -> Producto | None:
        return self._repositorio.get_by_id(producto_id)

    def consultar_imagen(self, producto_id: UUID) -> ImagenProducto | None:
        return self._repositorio.get_imagen_by_id(producto_id)

    def listar(self) -> list[Producto]:
        return self._repositorio.list_activos()

    def actualizar(self, dto: ActualizarProductoDTO) -> Producto:
        producto = self._repositorio.get_by_id(dto.id)
        if producto is None:
            raise ValueError("Producto no encontrado")
        if dto.nombre is not None:
            producto.nombre = dto.nombre
        if dto.categoria_id is not None:
            producto.categoria_id = dto.categoria_id
        if dto.precio is not None:
            producto.precio = dto.precio
        if dto.stock is not None:
            producto.stock = dto.stock
        if dto.descripcion is not None:
            producto.descripcion = dto.descripcion
        if dto.activo is not None:
            producto.activo = dto.activo
        if dto.material is not None:
            producto.material = dto.material
        if dto.tamano is not None:
            producto.tamano = dto.tamano
        if dto.color is not None:
            producto.color = dto.color
        if dto.specs is not None:
            producto.specs = dto.specs
        if dto.descuento is not None:
            producto.descuento = dto.descuento
            if dto.descuento > 0:
                producto.precio_original = _calcular_precio_original(producto.precio, dto.descuento)
            else:
                producto.precio_original = None
        return self._repositorio.update(producto)

    def eliminar(self, producto_id: UUID) -> None:
        producto = self._repositorio.get_by_id(producto_id)
        if producto is None:
            raise ValueError("Producto no encontrado")
        self._repositorio.delete(producto)

    def guardar_imagen(self, producto_id: UUID, imagen: ImagenProducto) -> None:
        self._repositorio.guardar_imagen(producto_id, imagen)
