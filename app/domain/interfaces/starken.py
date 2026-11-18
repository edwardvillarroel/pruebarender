
from abc import ABC, abstractmethod

from app.domain.entities.seguimiento_starken import SeguimientoStarken


class ErrorStarken(Exception):
    """Error al contactar el servicio de seguimiento de Starken."""


class StarkenSeguimientoCliente(ABC):


    @abstractmethod
    def consultar(self, codigo: str) -> SeguimientoStarken | None:

        raise NotImplementedError