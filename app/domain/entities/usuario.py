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
    apellido: str
    rol: Rol = Rol.CLIENTE
    activo: bool = True
    auth_provider: str = "local"
    google_sub: str | None = None
    mfa_secret: str | None = None
    mfa_activo: bool = False
    telefono: str | None = None
    id: UUID = field(default_factory=uuid4)
    creado_en: datetime = field(default_factory=utcnow)
