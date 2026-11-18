



from __future__ import annotations

from uuid import UUID

from app.domain.entities.pedido import Pedido
from app.domain.enums import EstadoPedido
from app.domain.interfaces.repositories import PedidoRepository


class AvisoPedidoNoEncontradoError(LookupError):

    def __init__(self) -> None:
        super().__init__("Pedido no encontrado")


class PedidoSinCancelarError(ValueError):

    def __init__(self) -> None:
        super().__init__(
            "Solo se puede avisar la anulacion de un pedido cancelado"
        )


class NotificarCancelacion:

    def __init__(self, pedidos: PedidoRepository) -> None:
        self._pedidos = pedidos

    def informar_cliente(self, pedido_id: UUID) -> Pedido:
        pedido = self._pedidos.get_by_id(pedido_id)
        if pedido is None:
            raise AvisoPedidoNoEncontradoError
        if pedido.estado is not EstadoPedido.CANCELADO:
            raise PedidoSinCancelarError
        actualizado = self._pedidos.marcar_aviso_cancelacion(pedido_id)
        if actualizado is None:  # pragma: no cover - carrera con un borrado
            raise AvisoPedidoNoEncontradoError
        return actualizado

    def marcar_visto(self, pedido_id: UUID) -> Pedido | None:
        pedido = self._pedidos.get_by_id(pedido_id)
        if pedido is None:
            raise AvisoPedidoNoEncontradoError
        if pedido.aviso_cancelacion_en is None or pedido.aviso_cancelacion_visto:
            return pedido
        return self._pedidos.marcar_aviso_cancelacion_visto(pedido_id)
