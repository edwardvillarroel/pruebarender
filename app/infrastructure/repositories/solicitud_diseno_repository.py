from typing import Any

from app.infrastructure.database.models.solicitud_diseno_model import SolicitudDisenoModel
from app.infrastructure.repositories.repository_base import RepositoryBase


class SolicitudDisenoRepository(RepositoryBase):
    model = SolicitudDisenoModel

    def list_por_estado(self, estado: str) -> list[SolicitudDisenoModel]:
        return self.model.query.filter_by(estado=estado).all()