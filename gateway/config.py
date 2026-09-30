import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("GATEWAY_SECRET_KEY", "dev-gateway-secret-change-me")
    # OJO: usar 127.0.0.1 y NO "localhost". En Windows "localhost" resuelve a ::1
    # primero, el backend escucha solo en IPv4 y cada request pagaba ~2s de
    # timeout de IPv6 antes de caer a 127.0.0.1. Se nota en cada pagina.
    BACKEND_INTERNAL_URL = os.getenv("BACKEND_INTERNAL_URL", "http://127.0.0.1:8000")
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
    # Plantilla dedicada para alertas de seguridad (5º fallo de login, etc.)
    EMAILJS_TEMPLATE_ALERTA = os.getenv("EMAILJS_TEMPLATE_ALERTA", "")

    # --- Google OAuth ---
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")

    # --- reCAPTCHA v2 (anti fuerza bruta) ---
    RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY", "")
    RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")

    # --- URL del frontend (callback de Google redirige aquí) ---
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")