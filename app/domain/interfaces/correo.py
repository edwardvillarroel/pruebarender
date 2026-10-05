
from abc import ABC, abstractmethod
from app.domain.entities.pedido import Pedido


class ErrorEnvioCorreo(Exception):
    """Falla al enviar el correo (red, o respuesta no 2xx del proveedor)."""


class ServicioCorreo(ABC):
    """Contrato de los correos que el sistema envía por su cuenta."""

    @abstractmethod
    def enviar_comprobante_pedido(
        self, pedido: Pedido, cliente_email: str, estado_pago: str
    ) -> None:
        """Manda el comprobante de `pedido`.

        `estado_pago` va aparte del pedido a propósito. `pedido.estado` es el
        estado de ENVIO (pendiente / en_produccion / enviado / entregado /
        cancelado) y en el comprobante no es lo que el cliente vino a ver: ahí
        quiere saber si su PAGO se concretó. El estado del envío lo mira en
        "Mis pedidos" y el admin en su panel, que es donde corresponde.
        """
        raise NotImplementedError