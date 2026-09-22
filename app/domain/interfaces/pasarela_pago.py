"""Interfaz de la pasarela de pagos (contrato del dominio).

La capa de aplicación orquesta el pago únicamente contra esta interfaz; la
implementación concreta (el agente de TUU) vive en `infrastructure`. Así la
comunicación con el proveedor externo queda aislada del negocio y se puede
sustituir sin tocar los casos de uso.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SolicitudPago:
    """Datos de negocio que exige la pasarela para abrir un intento de pago.

    `referencia` identifica el intento de forma única para la pasarela (en TUU
    es `x_reference` y siempre coincide con el id del pedido en ApoloVibes).
    Los datos de transporte y configuración del proveedor (URL de la tienda,
    de redirección/callback) los aporta la propia implementación de
    `PasarelaPago`, no el dominio.
    """

    monto: int
    referencia: str
    descripcion: str
    nombre_cliente: str
    email_cliente: str
    telefono_cliente: str


@dataclass
class ResultadoIntentoPago:
    """Respuesta de la pasarela al abrir un intento: dónde redirigir al cliente.

    `url` es la dirección del formulario de pago y `token` es el identificador
    del intento devuelto por la pasarela (en TUU coincide con la referencia).
    """

    url: str
    token: str


class ErrorPasarela(Exception):
    """La pasarela no pudo abrir/confirmar el intento de pago."""


class PasarelaPago(ABC):
    """Contrato que debe cumplir cualquier proveedor de pagos del sistema."""

    @abstractmethod
    def crear_intento(self, solicitud: SolicitudPago) -> ResultadoIntentoPago:
        """Crea el intento y devuelve la URL para redirigir al cliente."""
        raise NotImplementedError

    @abstractmethod
    def verificar_firma(self, parametros: dict[str, str]) -> bool:
        """Valida que los parámetros de la pasarela estén firmados por ella."""
        raise NotImplementedError