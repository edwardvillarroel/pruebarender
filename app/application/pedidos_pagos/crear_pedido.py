from typing import Any

from app.domain.interfaces.repositories import PedidoRepository


class CrearPedido:
    """Caso de uso: crear un pedido a partir del carrito del cliente."""

    def __init__(self, repositorio: PedidoRepository) -> None:
        self._repositorio = repositorio

    def ejecutar(self, dto: Any) -> Any:
        # TODO: validar stock, calcular total, persistir pedido + detalles
        raise NotImplementedError