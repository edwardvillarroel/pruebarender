"""Pruebas del listado de usuarios del panel de administracion.

El caso de uso solo transforma el modelo de lectura del repositorio en el DTO
que consume el frontend. Lo que se protege aca es el contrato: los nombres de
las metricas y que no se filtren datos sensibles del usuario (hash de
contrasena, secreto MFA, etc.).
"""

from unittest.mock import Mock
from uuid import uuid4

from app.application.usuarios.gestionar_usuarios import GestionarUsuarios
from app.domain.entities.usuario import UsuarioMetricas
from app.infrastructure.security.passwords import crear_hash


def _servicio(usuarios: list[UsuarioMetricas]) -> GestionarUsuarios:
    repositorio = Mock()
    repositorio.listar_con_metricas.return_value = usuarios
    return GestionarUsuarios(repositorio, crear_hash)


def test_lista_las_metricas_de_cada_usuario():
    usuario_id = uuid4()
    servicio = _servicio(
        [
            UsuarioMetricas(
                id=usuario_id,
                nombre="Maria",
                apellido="Torres",
                email="maria@example.com",
                rol="cliente",
                productos_comprados=7,
                pedidos_pagados=3,
                cotizaciones_pedidas=5,
                cotizaciones_aprobadas=2,
                cotizaciones_rechazadas=1,
            )
        ]
    )

    fila = servicio.listar()[0]

    assert fila == {
        "id": str(usuario_id),
        "nombre": "Maria",
        "apellido": "Torres",
        "nombre_completo": "Maria Torres",
        "email": "maria@example.com",
        "rol": "cliente",
        "activo": True,
        "productos_comprados": 7,
        "pedidos_pagados": 3,
        "cotizaciones_pedidas": 5,
        "cotizaciones_aprobadas": 2,
        "cotizaciones_rechazadas": 1,
    }


def test_no_expone_datos_sensibles():
    servicio = _servicio(
        [
            UsuarioMetricas(
                id=uuid4(),
                nombre="Ana",
                apellido="",
                email="ana@example.com",
                rol="cliente",
            )
        ]
    )

    fila = servicio.listar()[0]

    assert "password_hash" not in fila
    assert "mfa_secret" not in fila
    assert "google_sub" not in fila
    # Sin apellido, el nombre completo no arrastra espacios.
    assert fila["nombre_completo"] == "Ana"


def test_sin_usuarios_devuelve_lista_vacia():
    assert _servicio([]).listar() == []