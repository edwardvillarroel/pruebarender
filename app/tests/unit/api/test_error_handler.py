


from flask import abort




def test_error_no_encontrado_retorna_mensaje(app, client):
    respuesta = client.get("/api/recursos-que-no-existen")
    assert respuesta.status_code == 404
    assert respuesta.get_json()["mensaje"] == "Recurso no encontrado"




def test_error_solicitud_invalida_retorna_mensaje(app, client):
    @app.post("/api/error-test/bad-request")
    def _error_bad_request():
        abort(400)

    respuesta = client.post("/api/error-test/bad-request")
    assert respuesta.status_code == 400
    assert respuesta.get_json()["mensaje"] == "Solicitud inválida"




def test_error_endpoint_no_implementado_retorna_mensaje(app, client):
    respuesta = client.post("/api/ai/image-to-3d")
    assert respuesta.status_code == 501
    assert respuesta.get_json()["mensaje"] == "Endpoint no implementado"




def test_error_excepcion_no_manejada_retorna_500_generico(app, client):
    app.config["TESTING"] = False
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.get("/api/error-test")
    def _error_test():
        raise RuntimeError("boom interno")

    respuesta = client.get("/api/error-test")
    assert respuesta.status_code == 500
    assert respuesta.get_json()["mensaje"] == "Error interno del servidor"
