from dataclasses import dataclass

from app.domain.enums import Rol

# ============================================================
# TEMPORAL - CREDENCIALES HARDCODEADAS (ELIMINAR CUANDO SE IMPLEMENTE DB)
# ============================================================
ADMIN_USERNAME = "admin@admin.com"
ADMIN_PASSWORD = "admin123"
# ============================================================


class CredencialesInvalidas(ValueError):
    """Se lanza cuando usuario o contraseña no coinciden."""


@dataclass(frozen=True)
class SesionAdmin:
    username: str
    rol: str = Rol.ADMIN.value


def autenticar_admin(username: str, password: str) -> SesionAdmin:
    """Valida credenciales del administrador y devuelve su sesión.

    Temporal: mientras no exista la tabla de usuarios, compara contra
    ADMIN_USERNAME / ADMIN_PASSWORD definidos arriba.
    """
    if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        raise CredencialesInvalidas("Credenciales inválidas")
    return SesionAdmin(username=ADMIN_USERNAME)