
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

    _montar_frontend_produccion(app)

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


def _montar_frontend_produccion(app: Flask) -> None:
    """Sirve el build de React (ApoloVibes-frontend/dist) desde el gateway.

    Frontend y API quedan en el MISMO origen, asi `const BASE_URL = '/api'`
    del frontend funciona sin CORS. Como el build de Vite usa un `base`
    distinto de "/", tambien lo sirve bajo ese prefijo (FRONTEND_BASE_URL).
    Las rutas /api/* se las lleva el proxy (proxy_bp) y jamas llegan aqui.
    """
    dist = Path(str(app.config.get("FRONTEND_DIST", "")))
    if not dist.is_dir():
        return

    base = str(app.config.get("FRONTEND_BASE_URL", "/")).strip("/")
    ruta_base = f"/{base}" if base else ""

    def spa(ruta: str = ""):
        if ruta.startswith("api/"):
            return jsonify(mensaje="Recurso no encontrado"), 404
        archivo = dist / ruta
        if ruta and archivo.is_file():
            return send_from_directory(dist, ruta)
        return send_from_directory(dist, "index.html")

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