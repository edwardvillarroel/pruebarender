import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def _oracle_uri():
    """URI a Oracle Autonomous con wallet mTLS. Sin ORACLE_* se usa Postgres."""
    usuario = os.getenv("ORACLE_USER", "ADMIN")
    password = os.getenv("ORACLE_PASSWORD", "")
    dsn = os.getenv("ORACLE_DSN", "")
    if not dsn or not password:
        return None, {}
    wallet = os.getenv("ORACLE_WALLET_DIR", "")
    connect_args = {"tcp_connect_timeout": 15}
    if wallet:
        uri = f"oracle+oracledb://{usuario}:{quote_plus(password)}@{dsn}"
        connect_args.update({"config_dir": wallet, "wallet_location": wallet})
        wp = os.getenv("ORACLE_WALLET_PASSWORD", "")
        if wp:
            connect_args["wallet_password"] = wp
    else:
        uri = f"oracle+oracledb://{usuario}:{quote_plus(password)}@localhost/oracle"
        connect_args["dsn"] = dsn
    return uri, {"connect_args": connect_args}


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql://app:app@localhost:5432/print3d_dev"
    )
    SQLALCHEMY_ENGINE_OPTIONS = {}
    _oracle_uri, _oracle_engine_options = _oracle_uri()
    if _oracle_uri:
        SQLALCHEMY_DATABASE_URI = _oracle_uri
        SQLALCHEMY_ENGINE_OPTIONS = _oracle_engine_options
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")

    # Pasarela de pagos TUU (Pago Online de Haulmer)
    TUU_ACCOUNT_ID = os.getenv("TUU_ACCOUNT_ID", "62224230")
    TUU_SECRET_KEY = os.getenv(
        "TUU_SECRET_KEY",
        "yAk0dXTJLQzkeEWODsQWVpPX0bn7ND50qwoQrXgqqNiUyEpgxIPxPtoCgKeLNeh1upTw72JZx5O9x5IaAtPIGUAVcMNcsUSg3M0M8tgWdUb4F8qkS8I7rHpOUmZqzvfS",
    )
    TUU_API_URL = os.getenv(
        "TUU_API_URL", "https://frontend-api.payment.haulmer.dev/v1/payment"
    )
    TUU_SHOP_NAME = os.getenv("TUU_SHOP_NAME", "ApoloVibes")
    # URL a donde TUU notifica el resultado del pago (server-to-server). Debe
    # ser accesible públicamente; en producción siempre HTTPS.
    TUU_URL_CALLBACK = os.getenv(
        "TUU_URL_CALLBACK", "http://localhost:3000/api/pago/callback"
    )
    # URL a donde TUU redirige al cliente después de pagar/cancelar (frontend).
    TUU_URL_COMPLETE = os.getenv(
        "TUU_URL_COMPLETE", "http://localhost:5173/pago/retorno"
    )
    TUU_URL_CANCEL = os.getenv("TUU_URL_CANCEL", "http://localhost:5173/checkout")

    # Seguimiento Starken (portal developers.starken.cl). Credenciales de la
    # cuenta de la PYME; sin STARKEN_API_KEY el seguimiento queda deshabilitado.
    STARKEN_API_URL = os.getenv("STARKEN_API_URL", "https://gateway.starken.cl")
    STARKEN_API_KEY = os.getenv("STARKEN_API_KEY", "")
    STARKEN_SEGUIMIENTO_RUTA = os.getenv("STARKEN_SEGUIMIENTO_RUTA", "/orden-flete/of/")
    STARKEN_TIMEOUT = int(os.getenv("STARKEN_TIMEOUT", "10"))
    # Modo desarrollador: con STARKEN_MODO_SIMULACION activo se inyecta un
    # cliente simulado (estados deterministas por código) en vez del real.
    STARKEN_MODO_SIMULACION = os.getenv("STARKEN_MODO_SIMULACION", "")

    MAX_UPLOAD_SIZE = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "glb", "stl"}
    UPLOAD_FOLDER = BASE_DIR / "uploads"

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    FRONTEND_DIST = os.getenv(
        "FRONTEND_DIST", str(BASE_DIR.parent / "ApoloVibes-frontend" / "dist")
    )
    # Prefijo del build de Vite (vite.config.js usa base: "/ApoloVibes3D-Frontend/").
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "/ApoloVibes3D-Frontend/")

    JSON_SORT_KEYS = False


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL", "postgresql://app:app@localhost:5432/print3d_test"
    )
    SQLALCHEMY_ENGINE_OPTIONS = {}


class ProductionConfig(Config):
    DEBUG = False