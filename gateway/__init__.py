
import logging
import os
from pathlib import Path

from flask import Flask, jsonify, redirect, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from gateway.api.rate_limit import limiter
from gateway.config import Config

_log = logging.getLogger("gateway")


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    origenes = [
        origen.strip()
        for origen in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origen.strip()
    ]
    if "*" in origenes:
        _log.warning(
            "CORS_ORIGINS contiene '*'; se ignora porque las cookies exigen origen exacto."
        )
        origenes = [origen for origen in origenes if origen != "*"]
    CORS(app, origins=origenes, supports_credentials=True)
    JWTManager(app)
    limiter.init_app(app)

    @app.after_request
    def _cabeceras_seguridad(respuesta):
        respuesta.headers["X-Frame-Options"] = "DENY"
        if (respuesta.content_type or "").startswith("application/json"):
            respuesta.headers["Cache-Control"] = "no-store"
        if app.config.get("COOKIE_SECURE", True):
            respuesta.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
            respuesta.headers["X-Content-Type-Options"] = "nosniff"
            respuesta.headers["Referrer-Policy"] = "no-referrer"
        return respuesta

    from gateway.api import register_blueprints

    register_blueprints(app)

    _montar_frontend_produccion(app)

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


def _ruta_dist_absoluta(app: Flask) -> Path | None:

    valor = str(app.config.get("FRONTEND_DIST", "")).strip()
    if not valor:
        return None
    dist = Path(valor).resolve()
    if not dist.is_dir():
        return None
    return dist


def _montar_frontend_produccion(app: Flask) -> None:

    dist = _ruta_dist_absoluta(app)
    if dist is None:
        return

    base = str(app.config.get("FRONTEND_BASE_URL", "/")).strip("/")
    ruta_base = f"/{base}" if base else ""

    def spa(ruta: str = ""):
        if ruta.startswith("api/"):
            return jsonify(mensaje="Recurso no encontrado"), 404
        archivo = dist / ruta
        if ruta and archivo.is_file():
            return send_from_directory(dist, ruta, max_age=31536000)
        return send_from_directory(dist, "index.html", max_age=0)

    if ruta_base:
        @app.get(ruta_base, defaults={"ruta": ""}, strict_slashes=False)
        @app.get(f"{ruta_base}/<path:ruta>", strict_slashes=False)
        def spa_con_prefijo(ruta: str = ""):
            return spa(ruta)

        @app.get("/")
        def pagina_raiz():
            return redirect(ruta_base)
    else:
        @app.get("/", strict_slashes=False)
        @app.get("/<path:ruta>", strict_slashes=False)
        def spa_raiz(ruta: str = ""):
            return spa(ruta)