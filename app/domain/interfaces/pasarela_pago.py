

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SolicitudPago:


    monto: int
    referencia: str
    descripcion: str
    nombre_cliente: str
    email_cliente: str
    telefono_cliente: str
    apellido_cliente: str = ""


@dataclass
class ResultadoIntentoPago:


    url: str
    token: str


class ErrorPasarela(Exception):
    """La pasarela no pudo abrir/confirmar el intento de pago."""


class PasarelaPago(ABC):

    @abstractmethod
    def crear_intento(self, solicitud: SolicitudPago) -> ResultadoIntentoPago:
        raise NotImplementedError

    @abstractmethod
    def verificar_firma(self, parametros: dict[str, str]) -> bool:
        raise NotImplementedError