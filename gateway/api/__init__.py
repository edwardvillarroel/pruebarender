from flask import Flask


def register_blueprints(app: Flask) -> None:
    from gateway.api.routes.auth_routes import auth_bp
    from gateway.api.routes.health_routes import health_bp
    from gateway.api.routes.proxy_routes import proxy_bp

    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(proxy_bp, url_prefix="/api")
    app.register_blueprint(health_bp)