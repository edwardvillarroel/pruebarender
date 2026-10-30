from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.enums import Rol
from app.domain.time import utcnow


@dataclass
class Usuario:
    email: str
    password_hash: str
    nombre: str
    # `apellido` es NULL en la base para cuentas que no lo informaron (p. ej.
    # el admin inicial). La restriccion `CK_USUARIOS_APELLIDO` solo lo exige
    # para rol `cliente`.
    apellido: str | None
    rol: Rol = Rol.CLIENTE
    activo: bool = True
    auth_provider: str = "local"
    google_sub: str | None = None
    mfa_secret: str | None = None
    mfa_activo: bool = False
    telefono: str | None = None
    id: UUID = field(default_factory=uuid4)
    creado_en: datetime = field(default_factory=utcnow)
    # Soft delete del panel de administracion: la fila nunca se borra (pedidos,
    # cotizaciones y resenas la referencian). Con fecha, la cuenta queda fuera
    # de los listados y no puede iniciar sesion.
    eliminado_en: datetime | None = None


@dataclass
class UsuarioMetricas:
    """Usuario con las metricas que muestra el panel de administracion.

    Es un modelo de lectura (no una tabla): el repositorio lo arma con
    agregaciones SQL para no traer todos los pedidos y cotizaciones a memoria.

    - `productos_comprados`: unidades compradas en pedidos pagados (no cancelados).
    - `pedidos_pagados`: cantidad de esos pedidos (contexto de la metrica anterior).
    - `cotizaciones_pedidas`: solicitudes de diseno creadas por el usuario.
    - `cotizaciones_aprobadas` / `cotizaciones_rechazadas`: subconjunto por estado.
    """

    id: UUID
    nombre: str
    apellido: str | None
    email: str
    rol: str
    activo: bool = True
    productos_comprados: int = 0
    pedidos_pagados: int = 0
    cotizaciones_pedidas: int = 0
    cotizaciones_aprobadas: int = 0
    cotizaciones_rechazadas: int = 0

    @property
    def nombre_completo(self) -> str:
        return " ".join(parte for parte in (self.nombre, self.apellido) if parte).strip()
