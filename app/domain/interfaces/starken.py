"""Interfaz de dominio: cliente de seguimiento Starken (orden de flete)."""

from abc import ABC, abstractmethod

from app.domain.entities.seguimiento_starken import SeguimientoStarken


class ErrorStarken(Exception):
    """Error al contactar el servicio de seguimiento de Starken."""


class StarkenSeguimientoCliente(ABC):
    """Consultas de seguimiento contra la API de Starken.

    La capa de aplicación depende solo de esta interfaz (DI); la implementación
    HTTP vive en infraestructura.
    """

    @abstractmethod
    def consultar(self, codigo: str) -> SeguimientoStarken | None:
        """Estado actual de una orden de flete.

        Devuelve None cuando el servicio no está configurado (sin API key);
        lanza `ErrorStarken` si el proveedor no responde o devuelve error.
        """
        raise NotImplementedError