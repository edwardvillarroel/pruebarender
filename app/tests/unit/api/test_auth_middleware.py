"""Guardas de autenticación y roles del middleware (OWASP Top 10 2025, A01).

`requiere_sesion` exige el `X-User-Id` del gateway y `rol_requerido` exige
uno de los roles permitidos. Estos tests blindan el decorador puro (sin BD y
sin tocar los servicios): sin sesión -> 401; con rol ajeno -> 403; con rol
permitido -> pasa al endpoint.
"""

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


# ---------------------------------------------------------------------------
# Sesión
# ---------------------------------------------------------------------------


def test_solo_admin_sin_sesion_es_401(client_guardas):
    respuesta = client_guardas.get("/api/solo-admin")
    assert respuesta.status_code == 401
    assert respuesta.get_json()["mensaje"] == "Sesión requerida"


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------


def test_solo_admin_con_rol_cliente_es_403(client_guardas):
    respuesta = client_guardas.get("/api/solo-admin", headers=CABECERA_CLIENTE)
    assert respuesta.status_code == 403
    assert respuesta.get_json()["mensaje"] == "No autorizado"


def test_solo_admin_con_rol_admin_es_200(client_guardas):
    respuesta = client_guardas.get("/api/solo-admin", headers=CABECERA_ADMIN)
    assert respuesta.status_code == 200
    assert respuesta.get_json()["ok"] is True


# ---------------------------------------------------------------------------
# Frontera gateway -> backend (OWASP A01: Broken Access Control)
# ---------------------------------------------------------------------------


def test_solo_admin_con_secreto_interno_valido_es_200(client_guardas, app):
    """Con `INTERNAL_SECRET` configurado, el secreto del gateway habilita el acceso."""
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
    """Sin el secreto interno valido -> se rechaza antes de evaluar el rol.

    `requiere_sesion` (decorador exterior) valida la barrera interna y, al no
    estar la request firmada por el gateway, corta antes del check de rol.
    """
    app.config["INTERNAL_SECRET"] = "secreto-interno-test"

    respuesta = client_guardas.get(
        "/api/solo-admin",
        headers={
            "X-User-Id": "11111111-1111-1111-1111-111111111111",
            "X-User-Rol": "admin",
            # Sin X-Internal-Secret: la request no viene del gateway confiable.
        },
    )
    assert respuesta.status_code == 401
    assert respuesta.get_json()["mensaje"] == "Sesión requerida"


def test_sin_secreto_configurado_es_fail_closed(client_guardas, app):
    """Fail-closed: sin `INTERNAL_SECRET` no se acepta identidad confiable.

    Si el secreto compartido no esta configurado, el backend no puede
    distinguir un request del gateway de uno directo: rechaza toda sesion en
    lugar de confiar en `X-User-Id`/`X-User-Rol` (OWASP A01).
    """
    app.config["INTERNAL_SECRET"] = ""

    respuesta = client_guardas.get("/api/solo-admin", headers=CABECERA_ADMIN)

    assert respuesta.status_code == 401
    assert respuesta.get_json()["mensaje"] == "Sesión requerida"
