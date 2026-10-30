"""Hash de contrasenas del backend.

El gateway (`gateway/domain/seguridad.py`) es el dueno de la autenticacion y
guarda las contrasenas con bcrypt. Aca se usa exactamente la misma libreria y
el mismo formato para que un usuario creado desde el panel de administracion
pueda iniciar sesion por el gateway sin ninguna conversion ni migracion.
"""

import bcrypt


def crear_hash(password: str) -> str:
    """Hash bcrypt de una contrasena en texto plano."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
