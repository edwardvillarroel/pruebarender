
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

    from gateway.api import register_blueprints

    register_blueprints(app)

    if os.getenv("ORACLE_DSN"):
        from gateway.infrastructure.ddl import crear_tablas

        try:
            crear_tablas()
        except Exception:
            _log.warning("Oracle no disponible al iniciar; el gateway sigue.", exc_info=True)

    return app