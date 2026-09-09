from typing import Any

from app.application.common.dto import CrearCategoriaDTO
from app.domain.interfaces.repositories import ProductoRepository


class GestionarCategoria:
    """Caso de uso: CRUD de categorías del catálogo."""

    def __init__(self, repositorio: ProductoRepository) -> None:
        self._repositorio = repositorio

    def crear(self, dto: CrearCategoriaDTO) -> Any:
        raise NotImplementedError

    def listar(self) -> list[Any]:
        raise NotImplementedError

    def actualizar(self, categoria_id: Any, dto: CrearCategoriaDTO) -> Any:
        raise NotImplementedError

    def eliminar(self, categoria_id: Any) -> None:
        raise NotImplementedError