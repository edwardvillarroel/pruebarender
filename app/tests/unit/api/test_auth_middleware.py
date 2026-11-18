

import pytest
from flask import Blueprint, jsonify

from app.api.middleware.auth import requiere_sesion, rol_requerido, usuario_actual


guard_bp = Blueprint("auth_guards_test", __name__)


@guard_bp.get("/solo-admin")
@requiere_sesion()
@rol_requerido("admin")
def solo_admin():
    return jsonify(ok=True, usuario=usuario_actual())


@pytest.fixture
def client_guardas(app):
    app.register_blueprint(guard_bp, url_prefix="/api")
    return app.test_client()


CABECERA_ADMIN = {
    "X-User-Id": "11111111-1111-1111-1111-111111111111",
    "X-User-Rol": "admin",
    "X-Internal-Secret": "secreto-interno-test",
}
CABECERA_CLIENTE = {
    "X-User-Id": "11111111-1111-1111-1111-111111111111",
    "X-User-Rol": "cliente",
    "X-Internal-Secret": "secreto-interno-test",
}




def test_solo_admin_sin_sesion_es_401(client_guardas):
    respuesta = client_guardas.get("/api/solo-admin")
    assert respuesta.status_code == 401
    assert respuesta.get_json()["mensaje"] == "Sesión requerida"




def test_solo_admin_con_rol_cliente_es_403(client_guardas):
    respuesta = client_guardas.get("/api/solo-admin", headers=CABECERA_CLIENTE)
    assert respuesta.status_code == 403
    assert respuesta.get_json()["mensaje"] == "No autorizado"


def test_solo_admin_con_rol_admin_es_200(client_guardas):
    respuesta = client_guardas.get("/api/solo-admin", headers=CABECERA_ADMIN)
    assert respuesta.status_code == 200
    assert respuesta.get_json()["ok"] is True




def test_solo_admin_con_secreto_interno_valido_es_200(client_guardas, app):
    app.config["INTERNAL_SECRET"] = "secreto-interno-test"

    respuesta = client_guardas.get(
        "/api/solo-admin",
        headers={
            "X-User-Id": "11111111-1111-1111-1111-111111111111",
            "X-User-Rol": "admin",
            "X-Internal-Secret": "secreto-interno-test",
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.get_json()["ok"] is True


def test_solo_admin_con_secreto_interno_invalido_es_401(client_guardas, app):

    app.config["INTERNAL_SECRET"] = "secreto-interno-test"

    respuesta = client_guardas.get(
        "/api/solo-admin",
        headers={
            "X-User-Id": "11111111-1111-1111-1111-111111111111",
            "X-User-Rol": "admin",
        },
    )
    assert respuesta.status_code == 401
    assert respuesta.get_json()["mensaje"] == "Sesión requerida"


def test_sin_secreto_configurado_es_fail_closed(client_guardas, app):

    app.config["INTERNAL_SECRET"] = ""

    respuesta = client_guardas.get("/api/solo-admin", headers=CABECERA_ADMIN)

    assert respuesta.status_code == 401
    assert respuesta.get_json()["mensaje"] == "Sesión requerida"
