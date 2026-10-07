from app.infrastructure.database.models.notificacion_model import NotificacionModel
from app.infrastructure.repositories.repository_base import RepositoryBase


class NotificacionRepository(RepositoryBase):
    model = NotificacionModel