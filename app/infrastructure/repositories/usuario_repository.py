from typing import Any

from app.infrastructure.database.models.usuario_model import UsuarioModel
from app.infrastructure.repositories.repository_base import RepositoryBase


class UsuarioRepository(RepositoryBase):
    model = UsuarioModel

    def get_by_email(self, email: str) -> UsuarioModel | None:
        return self.model.query.filter_by(email=email).first()