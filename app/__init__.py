from pathlib import Path

from flask import Flask, jsonify, redirect, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from app.config import Config
from app.infrastructure.database.connection import db


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_class)

    CORS(app, origins=app.config.get("CORS_ORIGINS", "*"))
    jwt = JWTManager(app)
    db.init_app(app)

    _configurar_carrito(app)
    _configurar_catalogo(app)

    @jwt.unauthorized_loader
    def _no_autenticado(_razon):
        return jsonify(mensaje="No autenticado"), 401

    from app.api import register_blueprints

    register_blueprints(app)

    from app.api.middleware.error_handler import register_error_handlers

    register_error_handlers(app)

    _montar_frontend_produccion(app)

    return app


def _configurar_carrito(app: Flask) -> None:
    """Punto de composición del carrito (inyección de dependencias).

    La ruta del carrito lee el servicio desde `app.config`; así la capa API
    no depende de `infrastructure`. El carrito se persiste en la base de datos
    (tablas `carrito`/`carrito_items`) y pertenece al usuario del JWT.
    """
    from app.application.carrito.gestionar_carrito import GestionarCarrito
    from app.infrastructure.repositories.carrito_repository_bd import (
        CarritoRepositoryBd,
    )

    app.config["CARRITO_SERVICE"] = GestionarCarrito(CarritoRepositoryBd())


def _configurar_catalogo(app: Flask) -> None:
    """Punto de composición del catálogo (inyección de dependencias).

    Las rutas de catálogo leen los servicios desde `app.config`; así la capa
    API no depende de `infrastructure`. El catálogo se lee desde la base de
    datos (tablas `productos`/`categorias`). Importar los repositorios registra
    los modelos ORM con Flask-SQLAlchemy (productos y categorias).
    """
    from app.application.catalogo_stock.gestionar_categoria import (
        GestionarCategoria,
    )
    from app.application.catalogo_stock.gestionar_producto import GestionarProducto
    from app.infrastructure.repositories.categoria_repository import (
        CategoriaRepository,
    )
    from app.infrastructure.repositories.producto_repository import (
        ProductoRepository,
    )

    app.config["PRODUCTO_SERVICE"] = GestionarProducto(ProductoRepository())
    app.config["CATEGORIA_SERVICE"] = GestionarCategoria(CategoriaRepository())


def _montar_frontend_produccion(app: Flask) -> None:
    """Sirve el build de React (ApoloVibes-frontend/dist) si existe.

    Como el build de Vite usa un `base` distinto de "/", también lo sirve
    bajo ese prefijo (FRONTEND_BASE_URL). Nunca toca las rutas /api/*:
    esas vuelven JSON de error.
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