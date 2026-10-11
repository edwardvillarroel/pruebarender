
from __future__ import annotations
from uuid import UUID
import re
import unicodedata

from app.domain.entities.pedido import Pedido
from app.domain.entities.resena import Resena, ResenaPublica
from app.domain.enums import EstadoPedido
from app.domain.interfaces.repositories import (
    PedidoRepository,
    ProductoRepository,
    ResenaRepository,
)

MAX_COMENTARIO = 300
_PUNTUACION_PERMITIDA = set(".,;:!?¡¿()'\"-")

class EstrellasInvalidasError(ValueError):
    """Las estrellas no son un entero entre 1 y 5."""


class ComentarioInvalidoError(ValueError):
    """El comentario no es un texto valido (tipo o largo)."""


class PedidoNoEncontradoError(LookupError):
    """El pedido no existe."""


class NoAutorizadoError(PermissionError):
    """Quien reseña (o consulta) no es el dueño del pedido."""


class NoEntregadoError(Exception):
    """El pedido todavía no está `entregado`: no es elegible para reseñar."""


class ProductoNoEnPedidoError(LookupError):
    """El producto no figura en los detalles del pedido (o el pedido está vacío)."""


class GestionarResena:
    def __init__(
        self,
        resenas: ResenaRepository,
        pedidos: PedidoRepository,
        productos: ProductoRepository,
    ) -> None:
        self._resenas = resenas
        self._pedidos = pedidos
        self._productos = productos

    def registrar(
        self,
        usuario_id: UUID,
        pedido_id: UUID,
        producto_id: UUID,
        estrellas: int,
        comentario: str | None = None,
    ) -> Resena:
        estrellas_enteras = _estrellas_validas(estrellas)
        comentario_normalizado = _comentario_valido(comentario)

        pedido = self._pedidos.get_by_id(pedido_id)
        if pedido is None:
            raise PedidoNoEncontradoError("Pedido no encontrado")

        if str(pedido.usuario_id) != str(usuario_id):
            raise NoAutorizadoError("Solo el dueño del pedido puede reseñarlo")

        if pedido.estado != EstadoPedido.ENTREGADO:
            raise NoEntregadoError(
                "Solo se puede reseñar un pedido entregado"
            )

        if producto_id not in {d.producto_id for d in pedido.detalles}:
            raise ProductoNoEnPedidoError(
                "El producto no pertenece a este pedido"
            )

        resena = Resena(
            usuario_id=usuario_id,
            pedido_id=pedido_id,
            producto_id=producto_id,
            estrellas=estrellas_enteras,
            comentario=comentario_normalizado,
        )
        
        return self._resenas.crear(resena)

    def listar_por_pedido(
        self, usuario_id: UUID, pedido_id: UUID, es_admin: bool = False
    ) -> list[Resena]:
        pedido = self._pedidos.get_by_id(pedido_id)
        if pedido is None:
            raise PedidoNoEncontradoError("Pedido no encontrado")

        if not es_admin and str(pedido.usuario_id) != str(usuario_id):
            raise NoAutorizadoError("Solo el dueño del pedido puede ver sus reseñas")

        return self._resenas.listar_por_pedido(pedido_id)

    def listar_por_producto(self, producto_id: UUID) -> list[ResenaPublica]:
        """Listado publico de resenas de un producto (sin control de sesion)."""
        return self._resenas.listar_por_producto(producto_id)


def _estrellas_validas(estrellas) -> int:
    """Entero 1-5. `bool` cuenta como inválido (es un `int` en Python)."""
    if isinstance(estrellas, bool) or not isinstance(estrellas, int):
        raise EstrellasInvalidasError("Las estrellas deben ser un entero de 1 a 5")
    if not 1 <= estrellas <= 5:
        raise EstrellasInvalidasError("Las estrellas deben estar entre 1 y 5")
    return estrellas

def _caracter_permitido(c: str) -> bool:
    if c in (" ", "\n") or c in _PUNTUACION_PERMITIDA:
        return True
    return unicodedata.category(c)[0] in {"L", "N", "M"}


def _comentario_valido(comentario) -> str | None:
    if comentario is None:
        return None
    if not isinstance(comentario, str):
        raise ComentarioInvalidoError("Comentario inválido")

    texto = unicodedata.normalize("NFC", comentario)
    texto = texto.replace("\r\n", "\n").replace("\t", " ")
    texto = re.sub(r" {2,}", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip()

    if not texto:
        return None
    if len(texto) > MAX_COMENTARIO:
        raise ComentarioInvalidoError(
            f"El comentario no puede superar los {MAX_COMENTARIO} caracteres"
        )
    if not all(_caracter_permitido(c) for c in texto):
        raise ComentarioInvalidoError(
            "El comentario solo puede contener letras, números y puntuación básica"
        )
    return texto
