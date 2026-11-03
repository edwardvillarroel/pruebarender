from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.pedido import Pedido
from app.domain.entities.producto import Producto
from app.domain.entities.solicitud_diseno import SolicitudDiseno
from shared.correo.cliente import ErrorEnvioCorreo

__all__ = ["ErrorEnvioCorreo", "ServicioCorreo"]


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

    @abstractmethod
    def avisar_admin_pedido_pagado(
        self, pedido: Pedido, cliente_email: str, estado_pago: str
    ) -> None:
        """Avisa al admin que se confirmó el pago de un pedido."""
        raise NotImplementedError

    @abstractmethod
    def avisar_admin_nueva_cotizacion(self, solicitud: SolicitudDiseno) -> None:
        """Avisa al admin que ingresó una nueva solicitud de diseño."""
        raise NotImplementedError

    @abstractmethod
    def avisar_admin_stock_bajo(self, productos: list[Producto]) -> None:
        """Avisa al admin que uno o más productos quedaron en stock bajo."""
        raise NotImplementedError

    @abstractmethod
    def enviar_estado_cotizacion(
        self,
        solicitud: SolicitudDiseno,
        estado: str,
        precio: int | None = None,
    ) -> None:
        """Informa al cliente que su cotización fue aprobada o rechazada."""
        raise NotImplementedError
