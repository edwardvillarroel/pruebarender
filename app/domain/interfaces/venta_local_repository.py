from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.venta_local import SesionVenta, VentaLocal


class VentaLocalRepository(ABC):
    """Almacenamiento de sesiones de venta local y sus ventas.

    Las sesiones pertenecen a un usuario (el cajero/administrador) y agrupan
    las ventas registradas hasta su cierre.
    """

    @abstractmethod
    def crear_sesion(self, sesion: SesionVenta) -> SesionVenta:
        """Persiste una nueva sesión de venta abierta y la devuelve."""
        raise NotImplementedError

    @abstractmethod
    def obtener_sesion_por_id(self, sesion_id: UUID) -> SesionVenta | None:
        """Devuelve la sesión con el id indicado, o None si no existe."""
        raise NotImplementedError

    @abstractmethod
    def obtener_sesion_abierta_de(self, usuario_id: UUID) -> SesionVenta | None:
        """Devuelve la sesión abierta del usuario, o None si no tiene ninguna."""
        raise NotImplementedError

    @abstractmethod
    def registrar_venta(self, venta: VentaLocal) -> VentaLocal:
        """Persiste una venta con todos sus items en una única transacción.

        El caso de uso ya descarta ventas sobre sesiones cerradas; acá solo se
        persiste lo que llega.
        """
        raise NotImplementedError

    @abstractmethod
    def cerrar_sesion(self, sesion_id: UUID) -> SesionVenta | None:
        """Marca la sesión como cerrada y la devuelve, o None si no existe."""
        raise NotImplementedError

    @abstractmethod
    def listar_reportes(self, usuario_id: UUID | None = None) -> list[SesionVenta]:
        """Lista las sesiones cerradas (reportes), opcionalmente de un usuario."""
        raise NotImplementedError

    @abstractmethod
    def obtener_reporte(self, sesion_id: UUID) -> SesionVenta | None:
        """Devuelve la sesión cerrada con el id indicado, o None si no existe
        o todavía está abierta."""
        raise NotImplementedError

    @abstractmethod
    def obtener_ventas_de_sesion(self, sesion_id: UUID) -> list[VentaLocal]:
        """Devuelve las ventas de una sesión, con sus items."""
        raise NotImplementedError