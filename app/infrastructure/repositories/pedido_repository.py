from typing import Any
from uuid import UUID

from app.infrastructure.database.models.pedido_model import PedidoModel
from app.infrastructure.repositories.repository_base import RepositoryBase


class PedidoRepository(RepositoryBase):
    """Repositorio de pedidos (SQLAlchemy)."""

    model = PedidoModel

    def list_by_usuario(self, usuario_id: UUID) -> list[PedidoModel]:
        return self.model.query.filter_by(usuario_id=usuario_id).all()