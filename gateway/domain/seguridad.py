import base64
import io
import secrets
import uuid
from datetime import datetime, timezone, timedelta

import bcrypt
import pyotp
import qrcode


def generar_codigo(digitos: int = 6) -> str:
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



def generar_secreto_totp() -> str:
    return pyotp.random_base32()


def construir_otpauth_uri(email: str, secreto: str, emisor: str = "ApoloVibes") -> str:
    return pyotp.totp.TOTP(secreto).provisioning_uri(name=email, issuer_name=emisor)


def totp_qr_base64(email: str, secreto: str, emisor: str = "ApoloVibes") -> str:
    uri = construir_otpauth_uri(email, secreto, emisor)
    imagen = qrcode.make(uri)
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"


def verificar_totp(secreto: str, codigo: str) -> bool:
    if not secreto or not codigo:
        return False
    try:
        return pyotp.TOTP(secreto).verify(codigo, valid_window=1)
    except (TypeError, ValueError):
        return False


def generar_codigos_respaldo(cantidad: int = 8) -> list[str]:
    return [
        "-".join(
            "".join(secrets.choice("ABCDEFGHJKMNPQRSTVWXYZ23456789") for _ in range(5))
            for _ in range(2)
        )
        for _ in range(cantidad)
    ]


def normalizar_codigo_respaldo(codigo: str) -> str:
    return "".join(car for car in (codigo or "").upper() if car.isalnum())


def codigo_respaldo_a_hash(codigo: str) -> str:
    return crear_hash(normalizar_codigo_respaldo(codigo))


def verificar_codigo_respaldo(codigo: str, codigo_hash: str) -> bool:
    return verificar_password(normalizar_codigo_respaldo(codigo), codigo_hash)