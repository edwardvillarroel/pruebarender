"""OAuth 2.0 de Google (Authorization Code Flow) con Authlib.

Flujo resuelto por el gateway (nunca se expone GOOGLE_CLIENT_SECRET al navegador):
  1. `generar_url_autorizacion()`  -> el frontend redirige el navegador aquí.
  2. Google redirige de vuelta a `GOOGLE_REDIRECT_URI` con `code` y `state`.
  3. `intercambiar_codigo(code, state)` -> valida `state`, canjea el code por
     tokens y devuelve un perfil {sub, email, email_verified, nombre, apellido}.

El `state` es un token firmado (HMAC, expira en 5 min) para mitigar CSRF.
"""
import base64
import hashlib
import hmac
import secrets
import time

from authlib.integrations.requests_client import OAuth2Session
from gateway.config import Config

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

SCOPES = "openid email profile"
STATE_EXPIRA_SEG = 300


class GoogleOAuthError(Exception):
    """Fallo de configuración, state inválido o intercambio de code."""


def configurado_google() -> bool:
    return bool(Config.GOOGLE_CLIENT_ID and Config.GOOGLE_CLIENT_SECRET and Config.GOOGLE_REDIRECT_URI)


def _firmar(valor: str) -> str:
    firma = hmac.new(
        Config.SECRET_KEY.encode(), valor.encode(), hashlib.sha256
    ).digest()
    return base64.urlsafe_b64encode(firma).decode()


def crear_state() -> str:
    """State firmado: nonce + timestamp. Se valida en `verificar_state`."""
    nonce = secrets.token_urlsafe(16)
    timestamp = str(int(time.time()))
    valor = f"{nonce}|{timestamp}"
    return f"{valor}.{_firmar(valor)}"


def verificar_state(state: str) -> bool:
    """Valida firma y expiración del state."""
    try:
        valor, firma = (state or "").split(".", 1)
        if not hmac.compare_digest(_firmar(valor), firma):
            return False
        _, timestamp = valor.split("|", 1)
        edad = time.time() - int(timestamp)
        return 0 <= edad <= STATE_EXPIRA_SEG
    except (ValueError, IndexError, TypeError):
        return False


def generar_url_autorizacion() -> str:
    if not configurado_google():
        raise GoogleOAuthError("Google OAuth no está configurado (faltan GOOGLE_* en .env)")
    estado = crear_state()
    sesion = OAuth2Session(
        client_id=Config.GOOGLE_CLIENT_ID,
        redirect_uri=Config.GOOGLE_REDIRECT_URI,
        scope=SCOPES,
    )
    url, _ = sesion.create_authorization_url(GOOGLE_AUTH_URL, state=estado)
    return url


def intercambiar_codigo(code: str, state: str) -> dict:
    """Canjea el `code` por el perfil de Google.

    Devuelve {sub, email, email_verified, nombre, apellido}.
    Lanza GoogleOAuthError si algo falla; si Google no verifica el correo,
    el error es considerado NO permitido (no se crea cuenta).
    """
    if not configurado_google():
        raise GoogleOAuthError("Google OAuth no está configurado (faltan GOOGLE_* en .env)")
    if not code:
        raise GoogleOAuthError("Falta el código de autorización")
    if not verificar_state(state):
        raise GoogleOAuthError("State de OAuth inválido o expirado (posible CSRF)")

    sesion = OAuth2Session(
        client_id=Config.GOOGLE_CLIENT_ID,
        client_secret=Config.GOOGLE_CLIENT_SECRET,
        redirect_uri=Config.GOOGLE_REDIRECT_URI,
    )
    try:
        sesion.fetch_token(GOOGLE_TOKEN_URL, code=code)
        datos = sesion.get(GOOGLE_USERINFO_URL).json()
    except Exception as error:
        raise GoogleOAuthError(f"Google no devolvió un token válido: {error}")

    if int(datos.get("email_verified") or 0) != 1:
        raise GoogleOAuthError("Google no verificó el correo; cuenta no creada")

    return {
        "sub": str(datos.get("sub") or ""),
        "email": str(datos.get("email") or "").lower(),
        "email_verified": True,
        "nombre": (datos.get("given_name") or datos.get("name") or "").strip(),
        "apellido": (datos.get("family_name") or "").strip(),
    }