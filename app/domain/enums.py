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