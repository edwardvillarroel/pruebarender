from flask import Flask


def register_blueprints(app: Flask) -> None:
    from app.api.routes.cart_routes import cart_bp
    from app.api.routes.catalogo_routes import catalogo_bp
    from app.api.routes.diseno_routes import diseno_bp
    from app.api.routes.llm_routes import llm_bp
    from app.api.routes.pedido_routes import pedido_bp
    from app.api.routes.ventas_routes import venta_bp

    app.register_blueprint(cart_bp, url_prefix="/api")
    app.register_blueprint(catalogo_bp, url_prefix="/api")
    app.register_blueprint(pedido_bp, url_prefix="/api")
    app.register_blueprint(venta_bp, url_prefix="/api")
    app.register_blueprint(diseno_bp, url_prefix="/api")
    app.register_blueprint(llm_bp, url_prefix="/api")