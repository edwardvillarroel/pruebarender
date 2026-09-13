from typing import Any
from uuid import UUID

from app.application.common.dto import ActualizarProductoDTO, CrearProductoDTO
from app.domain.entities.producto import ImagenProducto, Producto
from app.domain.interfaces.repositories import ProductoRepository


class GestionarProducto:
    """Caso de uso: CRUD de productos del catálogo."""

    def __init__(self, repositorio: ProductoRepository) -> None:
        self._repositorio = repositorio

    def crear(self, dto: CrearProductoDTO) -> Any:
        # TODO: validar datos, persistir, loguear auditoria
        raise NotImplementedError

    def consultar(self, producto_id: UUID) -> Producto | None:
        return self._repositorio.get_by_id(producto_id)

    def consultar_imagen(self, producto_id: UUID) -> ImagenProducto | None:
        return self._repositorio.get_imagen_by_id(producto_id)

    def listar(self) -> list[Producto]:
        # Solo los activos: el catálogo público no muestra inactivos/sin stock.
        return self._repositorio.list_activos()

    def actualizar(self, dto: ActualizarProductoDTO) -> Any:
        raise NotImplementedError

    def eliminar(self, producto_id: Any) -> None:
        raise NotImplementedError