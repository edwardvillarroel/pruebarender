from enum import Enum


class Rol(str, Enum):
    ADMIN = "admin"
    CLIENTE = "cliente"


class EstadoPedido(str, Enum):
    PENDIENTE = "pendiente"
    EN_PRODUCCION = "en_produccion"
    ENVIADO = "enviado"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"


class EstadoPago(str, Enum):
    PENDIENTE = "pendiente"
    AUTORIZADO = "autorizado"
    COMPLETADO = "completado"
    FALLIDO = "fallido"
    REEMBOLSADO = "reembolsado"


class EstadoSolicitudDiseno(str, Enum):
    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"


class TipoMaterial(str, Enum):
    PLA = "PLA"
    PETG = "PETG"
    RESINA = "Resina"
    ABS = "ABS"


class EstadoTarea(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MedioPago(str, Enum):
    EFECTIVO = "efectivo"
    TUU = "tuu"


class EstadoSesionVenta(str, Enum):
    ABIERTA = "abierta"
    CERRADA = "cerrada"


class TipoDocumentoTributario(str, Enum):


    BOLETA = "boleta"
    FACTURA = "factura"

    @property
    def codigo_dte(self) -> int:
        return 39 if self is TipoDocumentoTributario.BOLETA else 33


class EstadoDocumentoTributario(str, Enum):
    PENDIENTE = "pendiente"
    EMITIDO = "emitido"
    ERROR = "error"


class MedioPagoFacturacion(int, Enum):


    EFECTIVO = 1
    TARJETA = 2
    TRANSFERENCIA = 3
    CHEQUE = 4
    OTRO = 5