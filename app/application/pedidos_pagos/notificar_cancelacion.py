"""Caso de uso: avisar al cliente que Tuu acepto anular su pedido.

El pedido cancelado no termina en el momento en que cambia de estado: si el
pago ya se hizo, hay una solicitud de anulacion contra Tuu. Cuando Tuu la acepta,
el admin necesita que el cliente se entere, y el cliente necesita una senal que
no dependa de que revise su correo.

Ese aviso es un dato del pedido, no un correo: `aviso_cancelacion_en` registra
cuando el admin confirmo la aceptacion y `aviso_cancelacion_visto` registra si
el cliente ya lo abrio. La diferencia entre ambos es lo que enciende el badge
en MisPedidos; abrir el aviso es la unica forma de apagarlo.

La llamada real a Tuu todavia no existe: este caso de uso solo publica el
resultado que el admin ya obtuvo. Cuando se implemente el cliente de Tuu, el
`informar_cliente` se dispara desde ahi en vez de desde un boton.
"""

from __future__ import annotations

from uuid import UUID

from app.domain.entities.pedido import Pedido
from app.domain.enums import EstadoPedido
from app.domain.interfaces.repositories import PedidoRepository


class AvisoPedidoNoEncontradoError(LookupError):
    """El pedido no existe."""

    def __init__(self) -> None:
        super().__init__("Pedido no encontrado")


class PedidoSinCancelarError(ValueError):
    """Solo un pedido cancelado puede tener un aviso de anulacion."""

    def __init__(self) -> None:
        super().__init__(
            "Solo se puede avisar la anulacion de un pedido cancelado"
        )


class NotificarCancelacion:
    """Publica el aviso de anulacion y lo marca como leido."""

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
        """Apaga el badge. Idempotente: sin aviso no hay nada que marcar."""
        pedido = self._pedidos.get_by_id(pedido_id)
        if pedido is None:
            raise AvisoPedidoNoEncontradoError
        if pedido.aviso_cancelacion_en is None or pedido.aviso_cancelacion_visto:
            return pedido
        return self._pedidos.marcar_aviso_cancelacion_visto(pedido_id)
