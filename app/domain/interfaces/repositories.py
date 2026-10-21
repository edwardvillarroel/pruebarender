from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from app.domain.entities.categoria import Categoria
from app.domain.entities.detalle_pedido import DetallePedido
from app.domain.entities.pago import Pago
from app.domain.entities.pedido import Pedido
from app.domain.entities.resena import Resena, ResenaPublica
from app.domain.entities.producto import (
    ColorProducto,
    FotoColorCatalogo,
    ImagenProducto,
    Producto,
    ProductoVendido,
)
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
    def listar_mas_vendidos(
        self, desde: datetime | None, limite: int
    ) -> list[ProductoVendido]:
        """Productos ordenados por unidades vendidas, de mas a menos.

        `desde` es la cota inferior de la ventana de venta (None = todo el
        historico). Solo cuenta lo pagado: un pedido sin pago completado no es
        una venta.
        """
        raise NotImplementedError

    @abstractmethod
    def get_imagen_by_id(self, producto_id: UUID) -> ImagenProducto | None:
      
        raise NotImplementedError

    @abstractmethod
    def get_thumb_by_id(self, producto_id: UUID) -> ImagenProducto | None:

        raise NotImplementedError

    @abstractmethod
    def guardar_thumb(self, producto_id: UUID, thumb: ImagenProducto) -> None:

        raise NotImplementedError

    @abstractmethod
    def list_colores(self, producto_id: UUID) -> list[ColorProducto]:
 
        raise NotImplementedError

    @abstractmethod
    def get_color_by_id(self, color_id: UUID) -> ColorProducto | None:
        raise NotImplementedError

    @abstractmethod
    def primera_imagen_color_por_producto(
        self, producto_ids: list[UUID]
    ) -> dict[UUID, FotoColorCatalogo]:

        raise NotImplementedError

    @abstractmethod
    def get_color_imagen_by_id(self, color_id: UUID) -> ImagenProducto | None:
    
        raise NotImplementedError

    @abstractmethod
    def get_color_thumb_by_id(self, color_id: UUID) -> ImagenProducto | None:
 
        raise NotImplementedError

    @abstractmethod
    def guardar_color_thumb(self, color_id: UUID, thumb: ImagenProducto) -> None:
       
        raise NotImplementedError

    @abstractmethod
    def guardar_color(
        self, producto_id: UUID, nombre: str, imagen: ImagenProducto
    ) -> ColorProducto:
      
        raise NotImplementedError

    @abstractmethod
    def eliminar_color(self, color_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    def descontar_stock(self, items: Sequence[tuple[UUID, int]]) -> bool:

        raise NotImplementedError


class CategoriaRepository(RepositoryBase[Categoria], ABC):
    pass


class PedidoRepository(RepositoryBase[Pedido], ABC):
    @abstractmethod
    def list_by_usuario(self, usuario_id: UUID) -> list[Pedido]:
        raise NotImplementedError

    @abstractmethod
    def list_todos(self) -> list[Pedido]:
        
        raise NotImplementedError

    @abstractmethod
    def list_pagados(self) -> list[Pedido]:
        raise NotImplementedError

    @abstractmethod
    def crear_con_detalles(
        self, pedido: Pedido, detalles: list[DetallePedido]
    ) -> Pedido:
        
        raise NotImplementedError

    @abstractmethod
    def actualizar_estado(
        self, pedido_id: UUID, estado: EstadoPedido
    ) -> Pedido | None:
        raise NotImplementedError

    @abstractmethod
    def actualizar_seguimiento(
        self,
        pedido_id: UUID,
        codigo_seguimiento: str | None,
        estado_seguimiento: str | None,
        actualizado_en: datetime | None,
        transportista: str | None = None,
    ) -> Pedido | None:

        raise NotImplementedError


class ClaveIdempotenciaOcupada(Exception):
    """Ya hay un pago `pendiente` con esa clave de idempotencia.

    La traduce la infraestructura, que es la unica capa que sabe que la
    unicidad la garantiza un indice unico de Postgres. `application` recibe
    esta excepcion en vez de `sqlalchemy.exc.IntegrityError` para no depender
    del motor: la carrera del doble click es una regla del negocio, no un
    detalle de SQL.
    """


class PagoRepository(RepositoryBase[Pago], ABC):
    @abstractmethod
    def get_by_token(self, token: str) -> Pago | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_pedido(self, pedido_id: UUID) -> Pago | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_clave_idempotencia(self, clave: str) -> Pago | None:
        raise NotImplementedError


class SolicitudDisenoRepository(RepositoryBase[SolicitudDiseno], ABC):
    @abstractmethod
    def list_por_estado(self, estado: str) -> list[SolicitudDiseno]:
        raise NotImplementedError


class ResenaDuplicadaError(Exception):
    """Ya existe una reseña del usuario para ese producto en ese pedido.

    La traduce la infraestructura, que es la única capa que sabe que la
    unicidad la garantiza el `UNIQUE (usuario_id, pedido_id, producto_id)` de
    Postgres. `application` recibe esta excepción en vez de
    `sqlalchemy.exc.IntegrityError` para no depender del motor: el doble
    submit del modal es una regla del negocio, no un detalle de SQL.
    """


class ResenaRepository(RepositoryBase[Resena], ABC):
    @abstractmethod
    def crear(self, resena: Resena) -> Resena:
        """INSERTa la reseña y recalcula `productos.rating`/`resenas_count`
        en la misma transacción. `ResenaDuplicadaError` si el triple ya existe.
        """
        raise NotImplementedError

    @abstractmethod
    def listar_por_pedido(self, pedido_id: UUID) -> list[Resena]:
        raise NotImplementedError

    @abstractmethod
    def listar_por_producto(self, producto_id: UUID) -> list[ResenaPublica]:
        """Resenas publicas de un producto, de la mas reciente a la mas vieja."""
        raise NotImplementedError

    @abstractmethod
    def obtener(
        self, usuario_id: UUID, pedido_id: UUID, producto_id: UUID
    ) -> Resena | None:
        raise NotImplementedError

    @abstractmethod
    def recalcular_stats_producto(self, producto_id: UUID) -> None:
        """Re-sincroniza los stats denormalizados del producto (re-seed/reparación)."""
        raise NotImplementedError