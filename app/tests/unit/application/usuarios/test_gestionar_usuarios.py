

from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.application.usuarios.gestionar_usuarios import (
    DatosUsuarioInvalidos,
    GestionarUsuarios,
)
from app.domain.entities.usuario import Usuario, UsuarioMetricas
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
    assert fila["nombre_completo"] == "Ana"


def test_sin_usuarios_devuelve_lista_vacia():
    assert _servicio([]).listar() == []


def _servicio_para(usuario: Usuario) -> GestionarUsuarios:
    repositorio = Mock()
    repositorio.buscar_por_id.return_value = usuario
    repositorio.actualizar.side_effect = lambda u: u
    repositorio.contar_admins_activos.return_value = 2
    repositorio.correo_en_uso.return_value = False
    return GestionarUsuarios(repositorio, crear_hash)


@pytest.mark.parametrize("email", ["vendedor@apolovibes.cl", "OTRO@APOLOVIBES.CL"])
def test_cambiar_rol_a_empleado_de_dominio_empresa(email):
    usuario = Usuario(
        email=email,
        password_hash="x",
        nombre="Vendedor",
        apellido="Vega",
    )

    resultado = _servicio_para(usuario).cambiar_rol(
        usuario.id, "empleado", uuid4()
    )

    assert resultado["rol"] == "empleado"


@pytest.mark.parametrize("email", ["vendedor@gmail.com", "empleado@apolovibes.cl.mx"])
def test_cambiar_rol_a_empleado_externo_se_rechaza(email):
    usuario = Usuario(
        email=email,
        password_hash="x",
        nombre="Vendedor",
        apellido="Vega",
    )

    with pytest.raises(DatosUsuarioInvalidos, match="@apolovibes.cl"):
        _servicio_para(usuario).cambiar_rol(usuario.id, "empleado", uuid4())


def test_crear_empleado_externo_se_rechaza():
    servicio = _servicio([])

    with pytest.raises(DatosUsuarioInvalidos, match="@apolovibes.cl"):
        servicio.crear(
            {
                "email": "vendedor@gmail.com",
                "nombre": "Vendedor",
                "apellido": "Vega",
                "rol": "empleado",
                "password": "password-segura",
            }
        )