from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.categoria import Categoria
from app.domain.entities.detalle_pedido import DetallePedido
from app.domain.entities.pago import Pago
from app.domain.entities.pedido import Pedido
from app.domain.entities.producto import ImagenProducto, Producto
from app.domain.entities.solicitud_diseno import SolicitudDiseno
from app.domain.entities.usuario import Usuario
from app.domain.enums import EstadoPedido
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

    @abstractmethod
    def get_imagen_by_id(self, producto_id: UUID) -> ImagenProducto | None:
        """Bytes y content-type de la imagen del producto, sin cargar el resto."""
        raise NotImplementedError


class CategoriaRepository(RepositoryBase[Categoria], ABC):
    pass


class PedidoRepository(RepositoryBase[Pedido], ABC):
    @abstractmethod
    def list_by_usuario(self, usuario_id: UUID) -> list[Pedido]:
        raise NotImplementedError

    @abstractmethod
    def crear_con_detalles(
        self, pedido: Pedido, detalles: list[DetallePedido]
    ) -> Pedido:
        """Persiste el pedido y sus líneas en una sola transacción."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_estado(
        self, pedido_id: UUID, estado: EstadoPedido
    ) -> Pedido | None:
        raise NotImplementedError


class PagoRepository(RepositoryBase[Pago], ABC):
    @abstractmethod
    def get_by_token(self, token: str) -> Pago | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_pedido(self, pedido_id: UUID) -> Pago | None:
        raise NotImplementedError


class SolicitudDisenoRepository(RepositoryBase[SolicitudDiseno], ABC):
    @abstractmethod
    def list_por_estado(self, estado: str) -> list[SolicitudDiseno]:
        raise NotImplementedError