from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.venta_local import SesionVenta, VentaLocal


class VentaLocalRepository(ABC):


    @abstractmethod
    def crear_sesion(self, sesion: SesionVenta) -> SesionVenta:
        raise NotImplementedError

    @abstractmethod
    def obtener_sesion_por_id(self, sesion_id: UUID) -> SesionVenta | None:
        raise NotImplementedError

    @abstractmethod
    def obtener_sesion_abierta_de(self, usuario_id: UUID) -> SesionVenta | None:
        raise NotImplementedError

    @abstractmethod
    def registrar_venta(self, venta: VentaLocal) -> VentaLocal:

        raise NotImplementedError

    @abstractmethod
    def cerrar_sesion(self, sesion_id: UUID) -> SesionVenta | None:
        raise NotImplementedError

    @abstractmethod
    def listar_reportes(self, usuario_id: UUID | None = None) -> list[SesionVenta]:
        raise NotImplementedError

    @abstractmethod
    def obtener_reporte(self, sesion_id: UUID) -> SesionVenta | None:
        raise NotImplementedError

    @abstractmethod
    def obtener_ventas_de_sesion(self, sesion_id: UUID) -> list[VentaLocal]:
        raise NotImplementedError