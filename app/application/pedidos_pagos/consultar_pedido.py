
from __future__ import annotations

from uuid import UUID

from app.domain.entities.pedido import Pedido
from app.domain.interfaces.repositories import PedidoRepository


class ConsultarPedido:

    def __init__(self, repositorio: PedidoRepository) -> None:
        self._repositorio = repositorio

    def por_id(self, pedido_id: UUID) -> Pedido | None:
        return self._repositorio.get_by_id(pedido_id)

    def del_usuario(self, usuario_id: UUID) -> list[Pedido]:
        return self._repositorio.list_by_usuario(usuario_id)