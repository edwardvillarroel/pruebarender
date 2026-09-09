from typing import Any

from app.domain.interfaces.repositories import PedidoRepository


class ConsultarPedido:
    """Caso de uso: obtener el detalle de un pedido (cliente/admin)."""

    def __init__(self, repositorio: PedidoRepository) -> None:
        self._repositorio = repositorio

    def por_id(self, pedido_id: Any) -> Any:
        raise NotImplementedError

    def del_usuario(self, usuario_id: Any) -> list[Any]:
        raise NotImplementedError