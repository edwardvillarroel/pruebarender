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