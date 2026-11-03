"""Envío de correo transaccional sobre la API HTTP de Resend."""

from shared.correo.cliente import ClienteCorreo, ErrorEnvioCorreo
from shared.correo.modelos import (
    Correo,
    CotizacionCorreo,
    DescuentoCorreo,
    ItemCorreo,
    PedidoCorreo,
    ProductoCorreo,
)

__all__ = [
    "ClienteCorreo",
    "Correo",
    "CotizacionCorreo",
    "DescuentoCorreo",
    "ErrorEnvioCorreo",
    "ItemCorreo",
    "PedidoCorreo",
    "ProductoCorreo",
]
