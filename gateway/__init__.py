
import logging
import os

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from gateway.api.rate_limit import limiter
from gateway.config import Config

_log = logging.getLogger("gateway")


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(
        app,
        origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
        supports_credentials=True,
    )
    JWTManager(app)
    limiter.init_app(app)

    @app.after_request
    def _cabeceras_seguridad(respuesta):
        # HSTS solo cuando la cookie va Secure (producción/HTTPS). En dev (http)
        # el navegador descartaría la header y rompería la navegación normal.
        if app.config.get("COOKIE_SECURE", True):
            respuesta.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
            respuesta.headers["X-Content-Type-Options"] = "nosniff"
            respuesta.headers["Referrer-Policy"] = "no-referrer"
        return respuesta

    from gateway.api import register_blueprints

    register_blueprints(app)

    # B4: fallo ruidoso sin base de datos. Antes esto se tragaba la excepcion y
    # el gateway arrancaba igual, de modo que un `.env` sin DSN se manifestaba
    # mucho despues como un 500 en /auth/login y no como un problema de arranque.
    # Ahora `pg_pool` levanta RuntimeError con el mensaje concreto si falta la
    # configuracion, y los errores de conexion/DDL se propagan.
    from gateway.infrastructure.ddl import crear_tablas

    try:
        crear_tablas()
    except Exception as exc:
        raise RuntimeError(
            "El gateway no pudo preparar su base de datos. "
            "Revisa DATABASE_URL/PG_DSN (o POSTGRES_*) y que la base sea "
            f"accesible. Causa original: {exc}"
        ) from exc

    return app