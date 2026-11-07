from __future__ import annotations
from uuid import UUID
from app.domain.entities.pedido import Pedido
from app.domain.enums import EstadoPedido
from app.domain.interfaces.repositories import PedidoRepository


TRANSICIONES_PERMITIDAS: frozenset[tuple[EstadoPedido, EstadoPedido]] = frozenset(
    {
        (EstadoPedido.PENDIENTE, EstadoPedido.ENTREGADO),
        (EstadoPedido.ENVIADO, EstadoPedido.ENTREGADO),
        (EstadoPedido.PENDIENTE, EstadoPedido.CANCELADO),
        (EstadoPedido.EN_PRODUCCION, EstadoPedido.CANCELADO),
    }
)

TRANSICIONES_RETIRO: frozenset[tuple[EstadoPedido, EstadoPedido]] = frozenset(
    {
        (EstadoPedido.PENDIENTE, EstadoPedido.ENVIADO),
        (EstadoPedido.EN_PRODUCCION, EstadoPedido.ENVIADO),
    }
)


class EstadoInvalidoError(ValueError):
    """El estado pedido no existe en `EstadoPedido`."""


class TransicionInvalidaError(ValueError):
    """El estado pedido no es alcanzable desde el estado actual del pedido."""


class PedidoNoEncontradoError(LookupError):
    """El pedido no existe."""


class PedidoDeOtroUsuarioError(PermissionError):
    """El pedido no pertenece al usuario que intenta cancelarlo."""


class CambiarEstadoPedido:
    """Caso de uso: el admin mueve un pedido de estado."""

    def __init__(self, pedidos: PedidoRepository) -> None:
        self._pedidos = pedidos

    def cancelar(self, pedido_id: UUID, usuario_id: UUID) -> Pedido:
        """Cancelacion pedida por el propio cliente.

        Misma regla de estado que el admin (hasta `en_produccion`), pero con
        dueño: el cliente solo cancela lo suyo. La transicion la decide
        `ejecutar`, no esta entrada, para que la regla viva en un solo lugar.
        """
        pedido = self._pedidos.get_by_id(pedido_id)
        if pedido is None:
            raise PedidoNoEncontradoError("Pedido no encontrado")
        if str(pedido.usuario_id) != str(usuario_id):
            raise PedidoDeOtroUsuarioError("No autorizado")
        return self.ejecutar(pedido_id, EstadoPedido.CANCELADO.value)

    def ejecutar(self, pedido_id: UUID, estado: str) -> Pedido:
        destino = self._parsear_estado(estado)
        pedido = self._pedidos.get_by_id(pedido_id)
        if pedido is None:
            raise PedidoNoEncontradoError("Pedido no encontrado")

        
        entrega = getattr(pedido, "entrega", None)
        es_retiro = str(getattr(entrega, "value", entrega) or "").lower() == "retiro"
        transicion = (pedido.estado, destino)
        permitida = transicion in TRANSICIONES_PERMITIDAS or (
            es_retiro and transicion in TRANSICIONES_RETIRO
        )

        if not permitida:
            raise TransicionInvalidaError(
                f"No se puede pasar un pedido de «{pedido.estado.value}» "
                f"a «{destino.value}»"
            )

        return self._pedidos.actualizar_estado(pedido_id, destino) or pedido

    @staticmethod
    def _parsear_estado(estado: str) -> EstadoPedido:
        texto = str(estado or "").strip().lower()
        if not texto:
            raise EstadoInvalidoError("Falta el estado del pedido")
        try:
            return EstadoPedido(texto)
        except ValueError:
            validos = ", ".join(e.value for e in EstadoPedido)
            raise EstadoInvalidoError(
                f"Estado «{estado}» inválido. Los estados válidos son: {validos}"
            ) from None