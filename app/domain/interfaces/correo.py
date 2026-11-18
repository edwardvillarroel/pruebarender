from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.pedido import Pedido
from app.domain.entities.producto import Producto
from app.domain.entities.solicitud_diseno import SolicitudDiseno
from shared.correo.cliente import ErrorEnvioCorreo

__all__ = ["ErrorEnvioCorreo", "ServicioCorreo"]


class ServicioCorreo(ABC):

    @abstractmethod
    def enviar_comprobante_pedido(
        self, pedido: Pedido, cliente_email: str, estado_pago: str
    ) -> None:

        raise NotImplementedError

    @abstractmethod
    def avisar_admin_pedido_pagado(
        self, pedido: Pedido, cliente_email: str, estado_pago: str
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def avisar_admin_nueva_cotizacion(self, solicitud: SolicitudDiseno) -> None:
        raise NotImplementedError

    @abstractmethod
    def avisar_admin_stock_bajo(self, productos: list[Producto]) -> None:
        raise NotImplementedError

    @abstractmethod
    def enviar_estado_cotizacion(
        self,
        solicitud: SolicitudDiseno,
        estado: str,
        precio: int | None = None,
    ) -> None:
        raise NotImplementedError
