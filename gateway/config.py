import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("GATEWAY_SECRET_KEY", "dev-gateway-secret-change-me")
    BACKEND_INTERNAL_URL = os.getenv("BACKEND_INTERNAL_URL", "http://localhost:8000")
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
    # --- EmailJS (envío real de correos del gateway) ---
    EMAILJS_PUBLIC_KEY = os.getenv("EMAILJS_PUBLIC_KEY", "")
    EMAILJS_PRIVATE_KEY = os.getenv("EMAILJS_PRIVATE_KEY", "")
    EMAILJS_SERVICE_ID = os.getenv("EMAILJS_SERVICE_ID", "")
    EMAILJS_TEMPLATE_ID = os.getenv("EMAILJS_TEMPLATE_ID", "")