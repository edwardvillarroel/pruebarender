from __future__ import annotations
from uuid import UUID
from app.domain.entities.pedido import Pedido
from app.domain.enums import EstadoPedido
from app.domain.interfaces.repositories import PedidoRepository


TRANSICIONES_PERMITIDAS: frozenset[tuple[EstadoPedido, EstadoPedido]] = frozenset(
    {
        (EstadoPedido.PENDIENTE, EstadoPedido.ENTREGADO),
        (EstadoPedido.ENVIADO, EstadoPedido.ENTREGADO),
    }
)


class EstadoInvalidoError(ValueError):
    """El estado pedido no existe en `EstadoPedido`."""


class TransicionInvalidaError(ValueError):
    """El estado pedido no es alcanzable desde el estado actual del pedido."""


class PedidoNoEncontradoError(LookupError):
    """El pedido no existe."""


class CambiarEstadoPedido:
    """Caso de uso: el admin mueve un pedido de estado."""

    def __init__(self, pedidos: PedidoRepository) -> None:
        self._pedidos = pedidos

    def ejecutar(self, pedido_id: UUID, estado: str) -> Pedido:
        destino = self._parsear_estado(estado)
        pedido = self._pedidos.get_by_id(pedido_id)
        if pedido is None:
            raise PedidoNoEncontradoError("Pedido no encontrado")

        if (pedido.estado, destino) not in TRANSICIONES_PERMITIDAS:
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