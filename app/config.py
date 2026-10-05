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

    _oracle_uri_val, _oracle_engine_options = _oracle_uri()

    _backend = os.getenv("DB_BACKEND", "postgres").strip().lower()

    if _backend == "oracle":
        if not _hay_oracle:
            raise RuntimeError(
                "DB_BACKEND=oracle pero falta ORACLE_DSN u ORACLE_PASSWORD en el entorno"
            )
        SQLALCHEMY_DATABASE_URI = _oracle_uri_val
        SQLALCHEMY_ENGINE_OPTIONS = _oracle_engine_options
    elif _backend == "postgres":
        SQLALCHEMY_DATABASE_URI = os.getenv(
            "DATABASE_URL", "postgresql://app:app@localhost:5432/print3d_dev"
        )

        SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    else:
        raise RuntimeError(
            f"DB_BACKEND invalido: {_backend!r}. Valores validos: 'oracle' o 'postgres'."
        )

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

    STARKEN_API_URL = os.getenv("STARKEN_API_URL", "https://gateway.starken.cl")
    STARKEN_API_KEY = os.getenv("STARKEN_API_KEY", "")
    STARKEN_SEGUIMIENTO_RUTA = os.getenv("STARKEN_SEGUIMIENTO_RUTA", "/orden-flete/of/")
    STARKEN_TIMEOUT = int(os.getenv("STARKEN_TIMEOUT", "10"))

    STARKEN_MODO_SIMULACION = os.getenv("STARKEN_MODO_SIMULACION", "")

    EMAILJS_PUBLIC_KEY = os.getenv("EMAILJS_PUBLIC_KEY", "")
    EMAILJS_PRIVATE_KEY = os.getenv("EMAILJS_PRIVATE_KEY", "")
    EMAILJS_SERVICE_ID = os.getenv("EMAILJS_SERVICE_ID", "")
    EMAILJS_TEMPLATE_COMPROBANTE = os.getenv("EMAILJS_TEMPLATE_COMPROBANTE", "")

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
    _backend_test = os.getenv("TEST_DB_BACKEND", "postgres").strip().lower()

    if _backend_test == "oracle":
        _test_dsn = os.getenv("TEST_ORACLE_DSN", "")
        if not _test_dsn:
            raise RuntimeError(
                "TEST_DB_BACKEND=oracle exige TEST_ORACLE_DSN. No se cae al "
                "ORACLE_DSN del .env a proposito: los tests de integracion "
                "escriben en la base y el esquema de Oracle es la fuente de "
                "verdad de la migracion."
            )
        _wallet_test = os.getenv("TEST_ORACLE_WALLET_DIR", "")
        _args_test: dict = {}
        if _wallet_test:
            _args_test["config_dir"] = _wallet_test
            _args_test["wallet_location"] = _wallet_test
        if os.getenv("TEST_ORACLE_WALLET_PASSWORD"):
            _args_test["wallet_password"] = os.getenv("TEST_ORACLE_WALLET_PASSWORD")
        SQLALCHEMY_DATABASE_URI = _test_dsn
        SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": _args_test}
    elif _backend_test == "postgres":
        SQLALCHEMY_DATABASE_URI = os.getenv(
            "TEST_DATABASE_URL", "postgresql://app:app@localhost:5432/print3d_test"
        )
        SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    else:
        raise RuntimeError(
            f"TEST_DB_BACKEND invalido: {_backend_test!r}. "
            "Valores validos: 'oracle' o 'postgres'."
        )


class ProductionConfig(Config):
    DEBUG = False