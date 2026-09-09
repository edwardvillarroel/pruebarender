from app.infrastructure.database.models.pago_model import PagoModel
from app.infrastructure.repositories.repository_base import RepositoryBase


class PagoRepository(RepositoryBase):
    """Repositorio de pagos (SQLAlchemy)."""

    model = PagoModel