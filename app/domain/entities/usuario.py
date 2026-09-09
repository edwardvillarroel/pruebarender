from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.enums import Rol


@dataclass
class Usuario:
    email: str
    password_hash: str
    nombre: str
    apellido: str
    rol: Rol = Rol.CLIENTE
    activo: bool = True
    telefono: str | None = None
    id: UUID = field(default_factory=uuid4)
    creado_en: datetime = field(default_factory=datetime.utcnow)