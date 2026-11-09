"""Contrato de errores de la API (OWASP Top 10 2025, A10 / A02).

Los handlers de error estandar del backend (`app/api/middleware/error_handler`)
deben responder siempre con el contrato acordado con el frontend:
`{ "mensaje": string }` — sin stack traces, sin detalles internos.

- 400: solicitud inválida.
- 401: no autenticado.
- 403: no autorizado.
- 404: recurso no encontrado.
- 429: demasiadas solicitudes.
- 500: error interno (genérico).
- NotImplementedError: endpoint pendiente (501).
"""

from flask import abort


# ---------------------------------------------------------------------------
# 404
# ---------------------------------------------------------------------------


def test_error_no_encontrado_retorna_mensaje(app, client):
    respuesta = client.get("/api/recursos-que-no-existen")
    assert respuesta.status_code == 404
    assert respuesta.get_json()["mensaje"] == "Recurso no encontrado"


# ---------------------------------------------------------------------------
# 400 (solicitud inválida)
# ---------------------------------------------------------------------------


def test_error_solicitud_invalida_retorna_mensaje(app, client):
    @app.post("/api/error-test/bad-request")
    def _error_bad_request():
        abort(400)

    respuesta = client.post("/api/error-test/bad-request")
    assert respuesta.status_code == 400
    assert respuesta.get_json()["mensaje"] == "Solicitud inválida"


# ---------------------------------------------------------------------------
# 501 (NotImplementedError)
# ---------------------------------------------------------------------------


def test_error_endpoint_no_implementado_retorna_mensaje(app, client):
    respuesta = client.post("/api/ai/image-to-3d")
    assert respuesta.status_code == 501
    assert respuesta.get_json()["mensaje"] == "Endpoint no implementado"


# ---------------------------------------------------------------------------
# 500 (error no manejado -> respuesta generica)
# ---------------------------------------------------------------------------


def test_error_excepcion_no_manejada_retorna_500_generico(app, client):
    # Sin TESTING/PROPAGATE_EXCEPTIONS el error cae al handler 500 del backend.
    app.config["TESTING"] = False
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.get("/api/error-test")
    def _error_test():
        raise RuntimeError("boom interno")

    respuesta = client.get("/api/error-test")
    assert respuesta.status_code == 500
    assert respuesta.get_json()["mensaje"] == "Error interno del servidor"
