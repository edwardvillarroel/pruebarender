from typing import Any
from uuid import UUID

from app.application.common.dto import CrearCategoriaDTO
from app.domain.entities.categoria import Categoria
from app.domain.interfaces.repositories import CategoriaRepository


class GestionarCategoria:
    """Caso de uso: CRUD de categorías del catálogo."""

    def __init__(self, repositorio: CategoriaRepository) -> None:
        self._repositorio = repositorio

    def crear(self, dto: CrearCategoriaDTO) -> Any:
        raise NotImplementedError

    def listar(self) -> list[Categoria]:
        return self._repositorio.list()

    def actualizar(self, categoria_id: UUID, dto: CrearCategoriaDTO) -> Any:
        raise NotImplementedError

    def eliminar(self, categoria_id: UUID) -> None:
        raise NotImplementedError