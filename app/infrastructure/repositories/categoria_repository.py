"""Repositorio de categorías (SQLAlchemy) con mapeo ORM -> dominio.

Implementa la interfaz `CategoriaRepository` de la capa de dominio; devuelve
entidades `Categoria`, no modelos ORM.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.domain.entities.categoria import Categoria
from app.domain.interfaces.repositories import (
    CategoriaRepository as CategoriaRepositoryInterface,
)
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.categoria_model import CategoriaModel


class CategoriaRepository(CategoriaRepositoryInterface):
    model = CategoriaModel

    def get_by_id(self, entity_id: UUID) -> Categoria | None:
        modelo = db.session.get(self.model, entity_id)
        return _a_entidad(modelo) if modelo else None

    def list(self, *filters: Any) -> list[Categoria]:
        consulta = db.session.query(self.model)
        if filters:
            consulta = consulta.filter(*filters)
        return [_a_entidad(m) for m in consulta.all()]

    def add(self, entidad: Categoria) -> Categoria:
        db.session.add(_a_modelo(entidad))
        return entidad

    def update(self, entidad: Categoria) -> Categoria:
        db.session.merge(_a_modelo(entidad))
        return entidad

    def delete(self, entidad: Categoria) -> None:
        modelo = db.session.get(self.model, entidad.id)
        if modelo is None:
            raise ValueError("Categoría no encontrada en BD")
        db.session.delete(modelo)
        db.session.commit()


def _a_entidad(modelo: CategoriaModel) -> Categoria:
    return Categoria(
        id=modelo.id,
        nombre=modelo.nombre,
        descripcion=modelo.descripcion,
    )


def _a_modelo(entidad: Categoria) -> CategoriaModel:
    return CategoriaModel(
        id=entidad.id,
        nombre=entidad.nombre,
        descripcion=entidad.descripcion,
    )