from flask import jsonify


def register_error_handlers(app) -> None:
    @app.errorhandler(400)
    def bad_request(_e):
        return jsonify(mensaje="Solicitud inválida"), 400

    @app.errorhandler(401)
    def unauthorized(_e):
        return jsonify(mensaje="No autenticado"), 401

    @app.errorhandler(403)
    def forbidden(_e):
        return jsonify(mensaje="No autorizado"), 403

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify(mensaje="Recurso no encontrado"), 404

    @app.errorhandler(429)
    def too_many_requests(_e):
        return jsonify(mensaje="Demasiadas solicitudes, intente más tarde"), 429

    @app.errorhandler(500)
    def internal_error(_e):
        return jsonify(mensaje="Error interno del servidor"), 500