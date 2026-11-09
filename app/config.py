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
    # OWASP A01: secreto compartido para la frontera gateway -> backend. El
    # gateway lo agrega como `X-Internal-Secret` al reenviar. Fail-closed: si no
    # esta configurado (o no coincide), el backend rechaza toda request
    # autenticada. Debe existir en local y en produccion (Render).
    INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "")
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
    # OWASP A04: sin secret embebido en codigo. El valor por defecto es vacio:
    # la key real (y el account) se toman de variables de entorno (Render en
    # produccion; .env en local). El fallback embebido anterior era solo una key
    # de pruebas y no debe vivir en el codigo fuente.
    TUU_SECRET_KEY = os.getenv("TUU_SECRET_KEY", "")
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

    # Correo transaccional (Resend). Sin RESEND_API_KEY o EMAIL_FROM el
    # sistema simula el envío (no llama a la API y no lanza).
    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
    EMAIL_FROM = os.getenv("EMAIL_FROM", "")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "https://apolovibes3d.cl")

    # Facturación electrónica (DTE) vía OpenFactura (Haulmer).
    # La API key se genera en https://openfactura.haulmer.com -> Configuración
    # -> API -> GENERAR API KEY, con la cuenta titular de la organización.
    OPENFACTURA_API_KEY = os.getenv("OPENFACTURA_API_KEY", "")
    OPENFACTURA_API_URL = os.getenv(
        "OPENFACTURA_API_URL", "https://api.haulmer.com"
    ).rstrip("/")
    OPENFACTURA_TIMEOUT = int(os.getenv("OPENFACTURA_TIMEOUT", "30"))

    # Emisor: los datos de la organización certificada ante el SII. Salen de
    # `GET /v2/dte/taxpayer/{rut}` de la propia API.
    EMISOR_RUT = os.getenv("EMISOR_RUT", "")
    EMISOR_RAZON_SOCIAL = os.getenv("EMISOR_RAZON_SOCIAL", "")
    EMISOR_GIRO = os.getenv("EMISOR_GIRO", "")
    EMISOR_DIRECCION = os.getenv("EMISOR_DIRECCION", "")
    EMISOR_COMUNA = os.getenv("EMISOR_COMUNA", "")
    EMISOR_ACTIVIDAD_ECONOMICA = os.getenv("EMISOR_ACTIVIDAD_ECONOMICA", "")
    EMISOR_CDG_SII_SUCUR = os.getenv("EMISOR_CDG_SII_SUCUR", "")

    MAX_UPLOAD_SIZE = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "glb", "stl"}
    UPLOAD_FOLDER = BASE_DIR / "uploads"

    # URLs firmadas de /api/uploads (F1): sin UPLOAD_SIGN_SECRET explícito se
    # firma con SECRET_KEY; TTL por defecto 24 h.
    UPLOAD_SIGN_SECRET = os.getenv("UPLOAD_SIGN_SECRET", "") or SECRET_KEY
    UPLOAD_SIGN_TTL_SECONDS = int(os.getenv("UPLOAD_SIGN_TTL_SECONDS", "86400"))
    # Secreto del cron de purga de cotizaciones (F3). Vacío => endpoint 503.
    CRON_SECRET = os.getenv("CRON_SECRET", "")

    # Supabase Storage para las imágenes de cotizaciones (F4). Sin URL + clave +
    # cubeta NO vacíos el sistema se queda en disco local, igual que siempre.
    # La cubeta es privada y el nombre tiene mayúscula inicial ("Cotizaciones"):
    # SIEMPRE sale de la variable de entorno, nunca del código.
    SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
    SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "")
    # TTL de las URL firmadas que devuelve el 302 de /api/uploads (corto a
    # propósito: la firma de F1 ya controla quién puede pedir el archivo).
    SUPABASE_SIGN_TTL_SECONDS = int(os.getenv("SUPABASE_SIGN_TTL_SECONDS", "300"))

    # OWASP A02: sin origenes explicitos no se habilita CORS (nunca "*").
    # En dev y prod la API y el frontend comparten origen (gateway/proxy), asi
    # que un valor vacio significa "misma origen" y no abre nada.
    CORS_ORIGINS = [
        origen.strip()
        for origen in os.getenv("CORS_ORIGINS", "").split(",")
        if origen.strip()
    ]
    FRONTEND_DIST = os.getenv(
        "FRONTEND_DIST", str(BASE_DIR.parent / "ApoloVibes-frontend" / "dist")
    )
   
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "/ApoloVibes3D-Frontend/")

    COTIZADOR_IA_URL = os.getenv("COTIZADOR_IA_URL", "http://127.0.0.1:8001")
    # El cotizador vive en otro servicio de Render (free tier) con cold-starts
    # de ~20 s, por eso el timeout por defecto es más alto que los 30 s del cliente.
    COTIZADOR_IA_TIMEOUT = int(os.getenv("COTIZADOR_IA_TIMEOUT", "60"))

    JSON_SORT_KEYS = False


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True

    # OWASP A01: el backend es fail-closed y exige `X-Internal-Secret` cuando
    # `INTERNAL_SECRET` no esta vacio. En tests se fija un secreto compartido y
    # el cliente de integracion lo agrega (simula la firma del gateway).
    INTERNAL_SECRET = os.getenv("TEST_INTERNAL_SECRET", "secreto-interno-test")

    # F4: los tests NUNCA hablan con Supabase Storage de verdad (el .env local
    # trae credenciales válidas y load_dotenv ya las cargó en Config). Cada test
    # que necesite el almacenamiento "configurado" setea app.config y stubbea
    # `AlmacenSupabaseStorage._request`.
    SUPABASE_URL = ""
    SUPABASE_SERVICE_KEY = ""
    SUPABASE_STORAGE_BUCKET = ""

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