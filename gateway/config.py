import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("GATEWAY_SECRET_KEY", "dev-gateway-secret-change-me")
    BACKEND_INTERNAL_URL = os.getenv("BACKEND_INTERNAL_URL", "http://127.0.0.1:8000")
    INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "")
    COTIZADOR_IA_TIMEOUT = int(os.getenv("COTIZADOR_IA_TIMEOUT", "60"))
    JWT_SECRET_KEY = os.getenv("GATEWAY_JWT_SECRET", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    COOKIE_SECURE = os.getenv("GATEWAY_COOKIE_SECURE", "true").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    COOKIE_SAMESITE = (
        os.getenv("GATEWAY_COOKIE_SAMESITE", "").strip().capitalize() or "Strict"
    )
    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
    EMAIL_FROM = os.getenv("EMAIL_FROM", "")

    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")

    RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY", "")
    RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")

    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

    FRONTEND_DIST = os.getenv(
        "FRONTEND_DIST",
        str(Path(__file__).resolve().parents[1] / "ApoloVibes-frontend" / "dist"),
    )
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "/ApoloVibes3D-Frontend/")