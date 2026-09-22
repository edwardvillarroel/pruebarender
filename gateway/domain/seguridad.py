import bcrypt
import secrets
import uuid
from datetime import datetime, timezone, timedelta


def generar_codigo(digitos: int = 6) -> str:
    """Código numérico aleatorio para verificación por correo."""
    minimo = 10 ** (digitos - 1)
    maximo = (10 ** digitos) - 1
    return str(secrets.randbelow(maximo - minimo + 1) + minimo)


def crear_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_password(password: str, hash_guardado: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hash_guardado.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def nuevo_jti() -> str:
    return str(uuid.uuid4())


def calcular_expiracion(minutos: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutos)


def a_utc(valor: datetime) -> datetime:
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def esta_expirado(expira_en: datetime) -> bool:
    return datetime.now(timezone.utc) >= a_utc(expira_en)


def es_reuso(registro: dict) -> bool:
    return bool(registro.get("revocado"))