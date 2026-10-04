from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from app.domain.entities.categoria import Categoria
from app.domain.entities.detalle_pedido import DetallePedido
from app.domain.entities.pago import Pago
from app.domain.entities.pedido import Pedido
from app.domain.entities.producto import (
    ColorProducto,
    FotoColorCatalogo,
    ImagenProducto,
    Producto,
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
    """Contrato de persistencia de productos y sus variantes de color.

    Nota sobre el thumbnail: no existe un metodo para invalidarlo a proposito.
    El thumbnail es un cache derivado del BLOB original, asi que su
    invalidacion es un invariante de persistencia — si se reemplaza la foto, el
    cache cae con ella — y ocurre dentro del propio metodo de escritura
    (`guardar_imagen`/`guardar_color`).     Exponerlo como operacion aparte
    permitiria el estado incoherente (foto nueva con thumbnail de la vieja) sin
    que nada lo garantizara.
    """

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

    @abstractmethod
    def get_thumb_by_id(self, producto_id: UUID) -> ImagenProducto | None:
        """Thumbnail ya generado del producto, o `None` si todavia no existe.

        El thumbnail se genera la primera vez que se pide y queda guardado; por
        eso esta lectura no lo produce, solo lo devuelve si ya esta cacheado.
        """
        raise NotImplementedError

    @abstractmethod
    def guardar_thumb(self, producto_id: UUID, thumb: ImagenProducto) -> None:
        """Guarda el thumbnail generado y descarta el anterior."""
        raise NotImplementedError

    @abstractmethod
    def list_colores(self, producto_id: UUID) -> list[ColorProducto]:
        """Colores del producto en orden, sin cargar los bytes de las imagenes.

        `ColorProducto.imagen_url` ya viene resuelta y es `None` cuando el color
        todavia no tiene foto.
        """
        raise NotImplementedError

    @abstractmethod
    def get_color_by_id(self, color_id: UUID) -> ColorProducto | None:
        raise NotImplementedError

    @abstractmethod
    def primera_imagen_color_por_producto(
        self, producto_ids: list[UUID]
    ) -> dict[UUID, FotoColorCatalogo]:
        """Foto del primer color de cada producto, en una sola consulta.

        Sirve para que el listado del catalogo muestre una foto en la tarjeta
        cuando el producto no tiene foto principal pero si variantes de color.
        Solo devuelve los productos que efectivamente tienen foto de color.
        """
        raise NotImplementedError

    @abstractmethod
    def get_color_imagen_by_id(self, color_id: UUID) -> ImagenProducto | None:
        """Bytes y content-type de la imagen de un color, sin cargar el resto."""
        raise NotImplementedError

    @abstractmethod
    def get_color_thumb_by_id(self, color_id: UUID) -> ImagenProducto | None:
        """Thumbnail ya generado de un color, o `None` si no existe todavia."""
        raise NotImplementedError

    @abstractmethod
    def guardar_color_thumb(self, color_id: UUID, thumb: ImagenProducto) -> None:
        """Guarda el thumbnail de un color y descarta el anterior."""
        raise NotImplementedError

    @abstractmethod
    def guardar_color(
        self, producto_id: UUID, nombre: str, imagen: ImagenProducto
    ) -> ColorProducto:
        """Crea o reemplaza el color del producto indicado y su imagen."""
        raise NotImplementedError

    @abstractmethod
    def eliminar_color(self, color_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    def descontar_stock(self, items: Sequence[tuple[UUID, int]]) -> bool:
        """Descuenta todos los items del pedido en una sola transaccion.

        `items` son pares `(producto_id, cantidad)`. Devuelve `True` si se
        descontaron todos, o `False` si alguno no tenia stock suficiente (o el
        producto no existe) - en ese caso no se descuenta ninguno.

        Es una operacion atomica y no un `update` de entidad a proposito: leer el
        stock, compararlo en Python y despues escribir abre una ventana en la que
        dos pagos concurrentes leen el mismo stock y ambos lo dan por bueno,
        vendiendo unidades que no existen. El descuento de stock es la unica
        operacion del dominio donde esa carrera produce perdida real, asi que el
        "leer, validar y escribir" vive dentro de una sentencia de SQL con la
        condicion `stock >= cantidad`, que la base de datos serializa sola.

        Todo-o-nada y no item por item porque el pedido es una unidad de negocio:
        descontar el primer producto y fallar en el segundo deja stock derivado
        para un pedido que la pasarela va a rechazar.
        """
        raise NotImplementedError


class CategoriaRepository(RepositoryBase[Categoria], ABC):
    pass


class PedidoRepository(RepositoryBase[Pedido], ABC):
    @abstractmethod
    def list_by_usuario(self, usuario_id: UUID) -> list[Pedido]:
        raise NotImplementedError

    @abstractmethod
    def list_todos(self) -> list[Pedido]:
        """Todos los pedidos, más recientes primero (vista admin con seguimiento)."""
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

    @abstractmethod
    def actualizar_seguimiento(
        self,
        pedido_id: UUID,
        codigo_seguimiento: str | None,
        estado_seguimiento: str | None,
        actualizado_en: datetime | None,
    ) -> Pedido | None:
        """Guarda el código de seguimiento (OF) y el último estado sincronizado."""
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