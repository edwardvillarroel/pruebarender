from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from app.domain.time import utcnow


class EstadoSolicitud(str, Enum):
    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"


@dataclass
class SolicitudDiseno:
    usuario_id: UUID
    nombre: str
    email: str
    material: str
    descripcion: str
    telefono: str | None = None
    alto: Decimal | None = None
    ancho: Decimal | None = None
    largo: Decimal | None = None
    unidad: str = "cm"
    cantidad: int = 1
    uso: str | None = None
    color: str | None = None
    imagen: str | None = None
    modelo_url: str | None = None
    precio: Decimal | None = None
    estado: EstadoSolicitud = EstadoSolicitud.PENDIENTE
    id: UUID = field(default_factory=uuid4)
    creado_en: datetime = field(default_factory=utcnow)
