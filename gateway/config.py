import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("GATEWAY_SECRET_KEY", "dev-gateway-secret-change-me")
    # OJO: usar 127.0.0.1 y NO "localhost". En Windows "localhost" resuelve a ::1
    # primero, el backend escucha solo en IPv4 y cada request pagaba ~2s de
    # timeout de IPv6 antes de caer a 127.0.0.1. Se nota en cada pagina.
    BACKEND_INTERNAL_URL = os.getenv("BACKEND_INTERNAL_URL", "http://127.0.0.1:8000")
    # OWASP A01: secreto compartido para la frontera gateway -> backend. El
    # backend exige este header en los endpoints que inyectan X-User-Id/Rol.
    INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "")
    JWT_SECRET_KEY = os.getenv("GATEWAY_JWT_SECRET", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    # En produccion (HTTPS) la cookie del refresh debe ir con Secure=True.
    # En desarrollo local (http) hay que apagarla o el navegador la descarta.
    COOKIE_SECURE = os.getenv("GATEWAY_COOKIE_SECURE", "true").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    # SameSite de las cookies de sesion. "Strict" es lo correcto cuando front y
    # API comparten dominio registrable (ej. apolovibes3d.cl y
    # api.apolovibes3d.cl): el navegador las manda igual porque son same-site.
    # "None" es solo para el caso cross-site (front en un dominio y API en
    # otro) y exige COOKIE_SECURE=True o el navegador descarta la cookie.
    COOKIE_SAMESITE = (
        os.getenv("GATEWAY_COOKIE_SAMESITE", "").strip().capitalize() or "Strict"
    )
    # --- Correo transaccional (Resend) ---
    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
    EMAIL_FROM = os.getenv("EMAIL_FROM", "")

    # --- Google OAuth ---
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")

    # --- reCAPTCHA v2 (anti fuerza bruta) ---
    RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY", "")
    RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")

    # --- URL del frontend (callback de Google redirige aquí) ---
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # --- Build estático de React que el gateway sirve en producción ---
    FRONTEND_DIST = os.getenv(
        "FRONTEND_DIST",
        str(Path(__file__).resolve().parents[1] / "ApoloVibes-frontend" / "dist"),
    )
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "/ApoloVibes3D-Frontend/")