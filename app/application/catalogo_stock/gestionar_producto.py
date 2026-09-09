from typing import Any

from app.application.common.dto import ActualizarProductoDTO, CrearProductoDTO
from app.domain.interfaces.repositories import ProductoRepository


class GestionarProducto:
    """Caso de uso: CRUD de productos del catálogo."""

    def __init__(self, repositorio: ProductoRepository) -> None:
        self._repositorio = repositorio

    def crear(self, dto: CrearProductoDTO) -> Any:
        # TODO: validar datos, persistir, loguear auditoria
        raise NotImplementedError

    def consultar(self, producto_id: Any) -> Any:
        raise NotImplementedError

    def listar(self) -> list[Any]:
        raise NotImplementedError

    def actualizar(self, dto: ActualizarProductoDTO) -> Any:
        raise NotImplementedError

    def eliminar(self, producto_id: Any) -> None:
        raise NotImplementedError