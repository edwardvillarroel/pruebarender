from pathlib import Path

from flask import Flask, jsonify, redirect, send_from_directory
from flask_cors import CORS

from app.api.json_provider import ProveedorJsonApp
from app.config import Config
from app.infrastructure.database.connection import db


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_class)
    app.json = ProveedorJsonApp(app)

    CORS(app, origins=app.config.get("CORS_ORIGINS", "*"))
    db.init_app(app)

    _configurar_carrito(app)
    _configurar_catalogo(app)
    _configurar_pedidos_pagos(app)
    _configurar_ventas(app)

    from app.api import register_blueprints

    register_blueprints(app)

    from app.api.middleware.error_handler import register_error_handlers

    register_error_handlers(app)

    _montar_frontend_produccion(app)

    return app


def _configurar_carrito(app: Flask) -> None:
    from app.application.carrito.gestionar_carrito import GestionarCarrito
    from app.infrastructure.repositories.carrito_repository_bd import (
        CarritoRepositoryBd,
    )

    app.config["CARRITO_SERVICE"] = GestionarCarrito(CarritoRepositoryBd())


def _configurar_catalogo(app: Flask) -> None:
    from app.application.catalogo_stock.gestionar_categoria import (
        GestionarCategoria,
    )
    from app.application.catalogo_stock.gestionar_producto import GestionarProducto
    from app.infrastructure.imagenes.conversor_raw import normalizar_imagen
    from app.infrastructure.imagenes.thumbnail import generar_thumbnail
    from app.infrastructure.repositories.categoria_repository import (
        CategoriaRepository,
    )
    from app.infrastructure.repositories.producto_repository import (
        ProductoRepository,
    )

    app.config["PRODUCTO_SERVICE"] = GestionarProducto(
        ProductoRepository(), generador_thumb=generar_thumbnail
    )
    app.config["CATEGORIA_SERVICE"] = GestionarCategoria(CategoriaRepository())
    app.config["CONVERSOR_IMAGEN"] = normalizar_imagen


def _configurar_pedidos_pagos(app: Flask) -> None:
    from app.application.pedidos_pagos.cambiar_estado_pedido import (
        CambiarEstadoPedido,
    )
    from app.application.pedidos_pagos.consultar_pedido import ConsultarPedido
    from app.application.pedidos_pagos.crear_pedido import CrearPedido
    from app.application.pedidos_pagos.procesar_pago import ProcesarPago
    from app.application.pedidos_pagos.seguimiento_starken import (
        GestionarSeguimientoStarken,
    )
    from app.infrastructure.correo.emailjs import EmailJsCorreo
    from app.infrastructure.pagos.tuu_client import TuuCliente
    from app.infrastructure.starken.starken_cliente import StarkenCliente
    from app.infrastructure.starken.starken_cliente_simulado import (
        StarkenClienteSimulado,
    )
    from app.infrastructure.database.models.usuario_model import UsuarioModel 
    from app.infrastructure.repositories.carrito_repository_bd import (
        CarritoRepositoryBd,
    )
    from app.infrastructure.repositories.pago_repository import PagoRepository
    from app.infrastructure.repositories.pedido_repository import PedidoRepository
    from app.infrastructure.repositories.producto_repository import (
        ProductoRepository,
    )

    pedidos = PedidoRepository()
    pagos = PagoRepository()
    productos = ProductoRepository()

    app.config["PEDIDO_SERVICE"] = CrearPedido(pedidos, productos)
    app.config["CONSULTA_PEDIDO_SERVICE"] = ConsultarPedido(pedidos)
    app.config["CAMBIAR_ESTADO_PEDIDO_SERVICE"] = CambiarEstadoPedido(pedidos)
    app.config["PAGO_SERVICE"] = ProcesarPago(
        pedidos,
        pagos,
        productos,
        TuuCliente(app.config),
        CarritoRepositoryBd(),
        EmailJsCorreo(app.config),
    )
    if str(app.config.get("STARKEN_MODO_SIMULACION", "")).strip().lower() in ("1", "true", "si", "yes"):
        cliente_starken = StarkenClienteSimulado(app.config)
    else:
        cliente_starken = StarkenCliente(app.config)
    app.config["SEGUIMIENTO_STARKEN_SERVICE"] = GestionarSeguimientoStarken(
        pedidos, cliente_starken
    )


def _configurar_ventas(app: Flask) -> None:
    """Punto de composición de la venta local (inyección de dependencias).

    La ruta de ventas lee el servicio desde `app.config`; así la capa API no
    depende de `infrastructure`. Importar los repositorios registra los modelos
    ORM de venta local con Flask-SQLAlchemy.
    """
    from app.application.venta_local.gestionar_venta_local import GestionarVentaLocal
    from app.infrastructure.database.models.usuario_model import UsuarioModel 
    from app.infrastructure.repositories.producto_repository import ProductoRepository
    from app.infrastructure.repositories.venta_local_repository import VentaLocalRepository

    app.config["VENTA_SERVICE"] = GestionarVentaLocal(
        VentaLocalRepository(), ProductoRepository()
    )


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