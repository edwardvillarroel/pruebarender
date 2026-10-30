"""Tests del apartado de gestión de usuarios del panel de admin.

Siguen el mismo patrón que test_usuarios_routes.py:
- Uso de fixtures `app` y `client` de pytest-flask
- Headers X-User-Id / X-User-Rol del gateway
- Mock del servicio inyectado via app.config["USUARIOS_SERVICE"]
"""

from unittest.mock import Mock, patch
import pytest
from uuid import uuid4

from app import create_app
from app.config import TestingConfig
from app.application.usuarios.gestionar_usuarios import (
    DatosUsuarioInvalidos,
    CorreoEnUso,
    OperacionNoPermitida,
)


CABECERA_ADMIN = {
    "X-User-Id": "11111111-1111-1111-1111-111111111111",
    "X-User-Rol": "admin",
}

CABECERA_CLIENTE = {
    "X-User-Id": "11111111-1111-1111-1111-111111111111",
    "X-User-Rol": "cliente",
}


def _mock_servicio_vacio():
    """Mock que simula un servicio vacío/sin usuarios."""
    servicio = Mock()
    servicio.listar.return_value = []
    servicio.crear.return_value = {
        "id": str(uuid4()),
        "nombre": "Nuevo",
        "apellido": "",
        "email": "nuevo@example.com",
        "nombre_completo": "Nuevo",
        "rol": "cliente",
        "activo": True,
    }
    servicio.cambiar_rol.return_value = {
        "id": "11111111-1111-1111-1111-111111111111",
        "nombre": "Maria",
        "apellido": "Torres",
        "email": "maria@example.com",
        "nombre_completo": "Maria Torres",
        "rol": "cliente",
        "activo": True,
    }
    servicio.cambiar_estado.return_value = {
        "id": "11111111-1111-1111-1111-111111111111",
        "nombre": "Maria",
        "apellido": "Torres",
        "email": "maria@example.com",
        "nombre_completo": "Maria Torres",
        "rol": "cliente",
        "activo": False,
    }
    servicio.eliminar.return_value = None
    return servicio


def _mock_servicio_con_uno():
    """Mock con un usuario y respuestas realistas."""
    servicio = Mock()
    usuario_id = "11111111-1111-1111-1111-111111111111"
    servicio.listar.return_value = [
        {
            "id": usuario_id,
            "nombre": "Maria",
            "apellido": "Torres",
            "email": "maria@example.com",
            "nombre_completo": "Maria Torres",
            "rol": "cliente",
            "activo": True,
            "productos_comprados": 7,
            "pedidos_pagados": 3,
            "cotizaciones_pedidas": 5,
            "cotizaciones_aprobadas": 2,
            "cotizaciones_rechazadas": 1,
        }
    ]
    servicio.crear.return_value = {
        "id": str(uuid4()),
        "nombre": "Nuevo",
        "apellido": "Usuario",
        "email": "nuevo@example.com",
        "nombre_completo": "Nuevo Usuario",
        "rol": "cliente",
        "activo": True,
    }
    servicio.cambiar_rol.return_value = {
        "id": usuario_id,
        "nombre": "Maria",
        "apellido": "Torres",
        "email": "maria@example.com",
        "nombre_completo": "Maria Torres",
        "rol": "admin",
        "activo": True,
    }
    servicio.cambiar_estado.return_value = {
        "id": usuario_id,
        "nombre": "Maria",
        "apellido": "Torres",
        "email": "maria@example.com",
        "nombre_completo": "Maria Torres",
        "rol": "admin",
        "activo": False,
    }
    servicio.eliminar.return_value = None
    return servicio


# ---------------------------------------------------------------------------
# Tests de acceso (frontera de confianza - mismo patrón que test_usuarios_routes.py)
# ---------------------------------------------------------------------------


def test_crear_requiere_sesion(client):
    """POST /api/usuarios sin login -> 401."""
    respuesta = client.post("/api/usuarios", json={"nombre": "X", "email": "x@y.cl"})
    assert respuesta.status_code == 401


def test_crear_rechaza_a_clientes(client):
    """POST /api/usuarios con rol cliente -> 403."""
    respuesta = client.post(
        "/api/usuarios",
        json={"nombre": "X", "email": "x@y.cl"},
        headers=CABECERA_CLIENTE,
    )
    assert respuesta.status_code == 403


# ---------------------------------------------------------------------------
# Tests de crear usuario
# ---------------------------------------------------------------------------


def test_crear_usuario_admin(client, app):
    """POST /api/usuarios con datos válidos -> 201."""
    app.config["USUARIOS_SERVICE"] = _mock_servicio_con_uno()

    respuesta = client.post(
        "/api/usuarios",
        json={
            "nombre": "Nuevo",
            "apellido": "Usuario",
            "email": "nuevo@example.com",
            "password": "Contraseña123",
            "rol": "cliente",
        },
        headers=CABECERA_ADMIN,
    )
    assert respuesta.status_code == 201


def test_crear_usuario_correo_duplicado(client, app):
    """POST /api/usuarios con correo en uso -> 409."""
    app.config["USUARIOS_SERVICE"] = _mock_servicio_con_uno()
    # El route captura CorreoEnUso y retorna 409
    app.config["USUARIOS_SERVICE"].crear.side_effect = CorreoEnUso(
        "Ya existe una cuenta con ese correo electrónico"
    )

    respuesta = client.post(
        "/api/usuarios",
        json={
            "nombre": "Otro",
            "apellido": "Tal",
            "email": "maria@example.com",  # ya existe en el mock
            "password": "Contraseña123",
            "rol": "cliente",
        },
        headers=CABECERA_ADMIN,
    )
    assert respuesta.status_code == 409


def test_crear_usuario_password_corta(client, app):
    """POST /api/usuarios con contraseña muy corta -> 400."""
    app.config["USUARIOS_SERVICE"] = _mock_servicio_con_uno()
    # El route captura DatosUsuarioInvalidos y retorna 400
    app.config["USUARIOS_SERVICE"].crear.side_effect = DatosUsuarioInvalidos(
        "La contraseña debe tener al menos 8 caracteres"
    )

    respuesta = client.post(
        "/api/usuarios",
        json={
            "nombre": "Sin",
            "apellido": "Pwd",
            "email": "sinpwd@example.com",
            "password": "123",  # menor a 8
            "rol": "cliente",
        },
        headers=CABECERA_ADMIN,
    )
    assert respuesta.status_code == 400


def test_crear_usuario_sin_apellido_cliente(client, app):
    """POST /api/usuarios rol cliente sin apellido -> 400 (regla de negocio)."""
    app.config["USUARIOS_SERVICE"] = _mock_servicio_con_uno()
    # El route captura DatosUsuarioInvalidos y retorna 400
    app.config["USUARIOS_SERVICE"].crear.side_effect = DatosUsuarioInvalidos(
        "El apellido es obligatorio para un cliente"
    )

    respuesta = client.post(
        "/api/usuarios",
        json={
            "nombre": "Cliente",
            "apellido": "",  # obligatorio para cliente por CK_USUARIOS_APELLIDO
            "email": "cliente_sin_apellido@example.com",
            "password": "Contraseña123",
            "rol": "cliente",
        },
        headers=CABECERA_ADMIN,
    )
    assert respuesta.status_code == 400


# ---------------------------------------------------------------------------
# Tests de cambiar rol
# ---------------------------------------------------------------------------


def test_cambiar_rol_admin_a_cliente(client, app):
    """PATCH /api/usuarios/<id>/rol: admin -> cliente -> 200."""
    app.config["USUARIOS_SERVICE"] = _mock_servicio_con_uno()

    respuesta = client.patch(
        "/api/usuarios/11111111-1111-1111-1111-111111111111/rol",
        json={"rol": "cliente"},
        headers=CABECERA_ADMIN,
    )
    assert respuesta.status_code == 200


def test_cambiar_rol_cliente_a_admin(client, app):
    """PATCH /api/usuarios/<id>/rol: cliente -> admin -> 200."""
    app.config["USUARIOS_SERVICE"] = _mock_servicio_con_uno()

    respuesta = client.patch(
        "/api/usuarios/11111111-1111-1111-1111-111111111111/rol",
        json={"rol": "admin"},
        headers=CABECERA_ADMIN,
    )
    assert respuesta.status_code == 200


def test_cambiar_rol_mismo_rol_sin_cambiar(client, app):
    """PATCH /api/usuarios/<id>/rol con mismo rol -> 200 (no hace nada)."""
    app.config["USUARIOS_SERVICE"] = _mock_servicio_con_uno()

    respuesta = client.patch(
        "/api/usuarios/11111111-1111-1111-1111-111111111111/rol",
        json={"rol": "cliente"},
        headers=CABECERA_ADMIN,
    )
    assert respuesta.status_code == 200


def test_cambiar_rol_prohibido_quitar_ultimo_admin(client, app):
    """PATCH /api/usuarios/<id>/rol: no permite quitarle el admin si es el último."""
    app.config["USUARIOS_SERVICE"] = _mock_servicio_con_uno()
    with patch.object(
        app.config["USUARIOS_SERVICE"], "contar_admins_activos", return_value=1
    ):
        # El route captura OperacionNoPermitida y retorna 409
        app.config["USUARIOS_SERVICE"].cambiar_rol.side_effect = OperacionNoPermitida(
            "No puedes quitarte tu propio rol de administrador"
        )

        respuesta = client.patch(
            "/api/usuarios/11111111-1111-1111-1111-111111111111/rol",
            json={"rol": "cliente"},
            headers=CABECERA_ADMIN,
        )
    assert respuesta.status_code == 409


# ---------------------------------------------------------------------------
# Tests de cambiar estado (bloqueo/desbloqueo)
# ---------------------------------------------------------------------------


def test_cambiar_estado_bloquear_admin(client, app):
    """PATCH /api/usuarios/<id>/estado: bloquear admin -> 200."""
    app.config["USUARIOS_SERVICE"] = _mock_servicio_con_uno()

    respuesta = client.patch(
        "/api/usuarios/11111111-1111-1111-1111-111111111111/estado",
        json={"activo": False},
        headers=CABECERA_ADMIN,
    )
    assert respuesta.status_code == 200


def test_cambiar_estado_desbloquear(client, app):
    """PATCH /api/usuarios/<id>/estado: desbloquear -> 200."""
    app.config["USUARIOS_SERVICE"] = _mock_servicio_con_uno()

    respuesta = client.patch(
        "/api/usuarios/11111111-1111-1111-1111-111111111111/estado",
        json={"activo": True},
        headers=CABECERA_ADMIN,
    )
    assert respuesta.status_code == 200


def test_cambiar_estado_prohibido_bloquear_ultimo_admin(client, app):
    """PATCH /api/usuarios/<id>/estado: no permite bloquear si es el último admin."""
    app.config["USUARIOS_SERVICE"] = _mock_servicio_con_uno()
    with patch.object(
        app.config["USUARIOS_SERVICE"], "contar_admins_activos", return_value=1
    ):
        # El route captura OperacionNoPermitida y retorna 409
        app.config["USUARIOS_SERVICE"].cambiar_estado.side_effect = OperacionNoPermitida(
            "Debe quedar al menos un administrador activo en el sistema"
        )

        respuesta = client.patch(
            "/api/usuarios/11111111-1111-1111-1111-111111111111/estado",
            json={"activo": False},
            headers=CABECERA_ADMIN,
        )
    assert respuesta.status_code == 409


def test_cambiar_estado_prohibido_bloquearse_propio(client, app):
    """PATCH /api/usuarios/<id>/estado: no permite bloquear propia cuenta."""
    servicio = _mock_servicio_con_uno()
    # El route lanza OperacionNoPermitida si el actor es el mismo usuario
    servicio.cambiar_estado.side_effect = OperacionNoPermitida(
        "No puedes bloquear tu propia cuenta"
    )
    app.config["USUARIOS_SERVICE"] = servicio

    respuesta = client.patch(
        "/api/usuarios/11111111-1111-1111-1111-111111111111/estado",
        json={"activo": False},
        headers={
            "X-User-Id": "11111111-1111-1111-1111-111111111111",
            "X-User-Rol": "admin",
        },
    )
    assert respuesta.status_code == 409


# ---------------------------------------------------------------------------
# Tests de eliminar (soft delete)
# ---------------------------------------------------------------------------


def test_eliminar_usuario_admin(client, app):
    """DELETE /api/usuarios/<id>: admin elimina usuario -> 200."""
    app.config["USUARIOS_SERVICE"] = _mock_servicio_con_uno()

    respuesta = client.delete(
        "/api/usuarios/11111111-1111-1111-1111-111111111111",
        headers=CABECERA_ADMIN,
    )
    assert respuesta.status_code == 200


def test_eliminar_prohibido_autoeliminacion(client, app):
    """DELETE /api/usuarios/<id>: no permite autoeliminación -> 409."""
    servicio = _mock_servicio_con_uno()
    # El route lanza OperacionNoPermitida si el actor es el mismo usuario
    servicio.eliminar.side_effect = OperacionNoPermitida(
        "No puedes eliminar tu propia cuenta"
    )
    app.config["USUARIOS_SERVICE"] = servicio

    respuesta = client.delete(
        "/api/usuarios/11111111-1111-1111-1111-111111111111",
        headers={
            "X-User-Id": "11111111-1111-1111-1111-111111111111",
            "X-User-Rol": "admin",
        },
    )
    # Cuando el usuario intenta eliminarse a sí mismo, el route retorna 409
    assert respuesta.status_code == 409


def test_eliminar_prohibido_ultimo_admin(client, app):
    """DELETE /api/usuarios/<id>: no permite eliminar el último admin."""
    from unittest.mock import patch

    servicio = _mock_servicio_con_uno()
    with patch.object(servicio, "contar_admins_activos", return_value=1):
        # El route captura OperacionNoPermitida y retorna 409
        servicio.eliminar.side_effect = OperacionNoPermitida(
            "Debe quedar al menos un administrador activo en el sistema"
        )
        app.config["USUARIOS_SERVICE"] = servicio

        respuesta = client.delete(
            "/api/usuarios/11111111-1111-1111-1111-111111111111",
            headers={
                "X-User-Id": "11111111-1111-1111-1111-111111111111",
                "X-User-Rol": "admin",
            },
        )
    # Cuando intenta eliminar el último admin, el route retorna 409
    assert respuesta.status_code == 409