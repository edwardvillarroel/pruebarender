from typing import Any
from uuid import UUID

from app.infrastructure.database.models.producto_model import ProductoModel
from app.infrastructure.repositories.repository_base import RepositoryBase


class ProductoRepository(RepositoryBase):
    """Repositorio de productos (SQLAlchemy)."""

    model = ProductoModel

    def get_by_categoria(self, categoria_id: UUID) -> list[ProductoModel]:
        return self.model.query.filter_by(categoria_id=categoria_id).all()

    def list_activos(self) -> list[ProductoModel]:
        return self.model.query.filter_by(activo=True).all()