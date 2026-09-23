"""Entidades de dominio: resultados de seguimiento Starken.

Solo datos planos (sin SQLAlchemy/Flask); la capa de infraestructura traduce
la respuesta JSON del proveedor a estas entidades.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class EventoSeguimiento:
    """Hito del historial de una orden de flete."""

    fecha: datetime | None = None
    descripcion: str | None = None
    sucursal: str | None = None
    ciudad: str | None = None
    estado: str | None = None


@dataclass
class SeguimientoStarken:
    """Estado actual de una orden de flete (OF) consultada en Starken."""

    codigo: str
    estado: str | None = None
    descripcion: str | None = None
    historial: list[EventoSeguimiento] = field(default_factory=list)
    consultado_en: datetime = field(default_factory=datetime.utcnow)