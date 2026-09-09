from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.pedido import Pedido
from app.domain.entities.producto import Producto
from app.domain.entities.solicitud_diseno import SolicitudDiseno
from app.domain.entities.usuario import Usuario
from app.domain.interfaces.repository_base import RepositoryBase


class UsuarioRepository(RepositoryBase[Usuario], ABC):
    @abstractmethod
    def get_by_email(self, email: str) -> Usuario | None:
        raise NotImplementedError


class ProductoRepository(RepositoryBase[Producto], ABC):
    @abstractmethod
    def get_by_categoria(self, categoria_id: UUID) -> list[Producto]:
        raise NotImplementedError

    @abstractmethod
    def list_activos(self) -> list[Producto]:
        raise NotImplementedError


class PedidoRepository(RepositoryBase[Pedido], ABC):
    @abstractmethod
    def list_by_usuario(self, usuario_id: UUID) -> list[Pedido]:
        raise NotImplementedError


class SolicitudDisenoRepository(RepositoryBase[SolicitudDiseno], ABC):
    @abstractmethod
    def list_por_estado(self, estado: str) -> list[SolicitudDiseno]:
        raise NotImplementedError