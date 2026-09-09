from typing import Any


class ProcesarPago:
    """Caso de uso: inicio y confirmación de pago (Transbank Webpay Plus)."""

    def iniciar(self, dto: Any) -> Any:
        # TODO: crear Pago pendiente, llamar SDK Transbank, devolver {url, token}
        raise NotImplementedError

    def confirmar(self, token: str) -> Any:
        # TODO: confirmar con Transbank, actualizar estado del pago y del pedido
        raise NotImplementedError

    def anular(self, pago_id: Any) -> Any:
        raise NotImplementedError