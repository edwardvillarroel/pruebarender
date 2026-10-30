"""Tests del listado de usuarios del panel admin (`GET /api/usuarios`).

Se cubren los guard de acceso (misma frontera de confianza que el resto del
panel: headers del gateway) y el shape del payload que consume el frontend.
"""

from unittest.mock import Mock

CABECERA_ADMIN = {
    "X-User-Id": "11111111-1111-1111-1111-111111111111",
    "X-User-Rol": "admin",
}


def _servicio_con_datos() -> Mock:
    servicio = Mock()
    servicio.listar.return_value = [
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "nombre": "Maria",
            "apellido": "Torres",
            "nombre_completo": "Maria Torres",
            "email": "maria@example.com",
            "rol": "cliente",
            "productos_comprados": 7,
            "pedidos_pagados": 3,
            "cotizaciones_pedidas": 5,
            "cotizaciones_aprobadas": 2,
            "cotizaciones_rechazadas": 1,
        }
    ]
    return servicio


def test_el_listado_requiere_sesion(app, client):
    respuesta = client.get("/api/usuarios")
    assert respuesta.status_code == 401
    assert respuesta.get_json()["mensaje"] == "Sesión requerida"


def test_el_listado_rechaza_a_clientes(app, client):
    respuesta = client.get(
        "/api/usuarios",
        headers={
            "X-User-Id": "11111111-1111-1111-1111-111111111111",
            "X-User-Rol": "cliente",
        },
    )
    assert respuesta.status_code == 403
    assert respuesta.get_json()["mensaje"] == "No autorizado"


def test_el_listado_admin_devuelve_usuarios_y_metricas(app, client):
    app.config["USUARIOS_SERVICE"] = _servicio_con_datos()

    respuesta = client.get("/api/usuarios", headers=CABECERA_ADMIN)

    assert respuesta.status_code == 200
    usuarios = respuesta.get_json()["usuarios"]
    assert len(usuarios) == 1
    assert usuarios[0]["nombre_completo"] == "Maria Torres"
    assert usuarios[0]["email"] == "maria@example.com"
    assert usuarios[0]["productos_comprados"] == 7
    assert usuarios[0]["cotizaciones_pedidas"] == 5
    assert usuarios[0]["cotizaciones_aprobadas"] == 2
    assert usuarios[0]["cotizaciones_rechazadas"] == 1


def test_el_listado_admin_sin_usuarios_devuelve_lista_vacia(app, client):
    servicio = Mock()
    servicio.listar.return_value = []
    app.config["USUARIOS_SERVICE"] = servicio

    respuesta = client.get("/api/usuarios", headers=CABECERA_ADMIN)

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"usuarios": []}
