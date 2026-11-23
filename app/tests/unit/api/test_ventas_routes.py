from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest


ID_USUARIO = uuid4()
ID_SESION = uuid4()
ID_PRODUCTO = uuid4()

RUTAS_VENTA = [
    ("post", "/api/ventas/sesiones", {"lugar": "Feria"}),
    ("get", "/api/ventas/sesiones/actual", None),
    (
        "post",
        f"/api/ventas/sesiones/{ID_SESION}/ventas",
        {
            "medio_pago": "efectivo",
            "items": [{"producto_id": str(ID_PRODUCTO), "cantidad": 1}],
        },
    ),
    ("post", f"/api/ventas/sesiones/{ID_SESION}/cierre", None),
]


@pytest.fixture
def client_ventas(app):
    servicio = Mock()
    sesion = SimpleNamespace(
        id=ID_SESION,
        usuario_id=ID_USUARIO,
        lugar="Feria",
        fecha=date.today(),
        estado="abierta",
        creado_en=None,
        cerrada_en=None,
    )
    venta = SimpleNamespace(
        id=uuid4(),
        sesion_id=ID_SESION,
        usuario_id=ID_USUARIO,
        medio_pago="efectivo",
        total=100,
        creado_en=None,
        items=[],
    )
    servicio.abrir_sesion.return_value = sesion
    servicio.obtener_sesion_abierta.return_value = sesion
    servicio.registrar_venta.return_value = venta
    servicio.obtener_ventas_de_sesion.return_value = []
    servicio.cerrar_sesion.return_value = sesion
    servicio.listar_reportes.return_value = []
    app.config["VENTA_SERVICE"] = servicio
    return app.test_client()


def _cabeceras(rol: str) -> dict:
    return {
        "X-User-Id": str(ID_USUARIO),
        "X-User-Rol": rol,
        "X-Internal-Secret": "secreto-interno-test",
    }


@pytest.mark.parametrize("metodo,ruta,cuerpo", RUTAS_VENTA)
def test_empleado_puede_operar_su_sesion_de_venta(
    client_ventas, metodo, ruta, cuerpo
):
    respuesta = getattr(client_ventas, metodo)(ruta, json=cuerpo, headers=_cabeceras("empleado"))

    assert respuesta.status_code in (200, 201)


@pytest.mark.parametrize("metodo,ruta,cuerpo", RUTAS_VENTA)
def test_cliente_no_puede_operar_sesiones_de_venta(
    client_ventas, metodo, ruta, cuerpo
):
    respuesta = getattr(client_ventas, metodo)(ruta, json=cuerpo, headers=_cabeceras("cliente"))

    assert respuesta.status_code == 403
    assert respuesta.get_json()["mensaje"] == "No autorizado"


@pytest.mark.parametrize("rol", ["empleado", "cliente"])
def test_reportes_de_venta_siguen_siendo_solo_admin(client_ventas, rol):
    respuesta = client_ventas.get("/api/ventas/reportes", headers=_cabeceras(rol))

    assert respuesta.status_code == 403


def test_registrar_venta_queda_auditado(client_ventas, app):
    client_ventas.post(
        f"/api/ventas/sesiones/{ID_SESION}/ventas",
        json=RUTAS_VENTA[2][2],
        headers=_cabeceras("empleado"),
    )

    auditoria = app.config["AUDITORIA_SERVICE"]
    assert auditoria.registrar.called
    assert auditoria.registrar.call_args.args[0] == "registrar_venta"


@pytest.mark.parametrize("cantidad", [1.5, "2.5", True])
def test_la_ruta_rechaza_cantidades_no_enteras(client_ventas, cantidad):
    cuerpo = {
        "medio_pago": "efectivo",
        "items": [{"producto_id": str(ID_PRODUCTO), "cantidad": cantidad}],
    }

    respuesta = client_ventas.post(
        f"/api/ventas/sesiones/{ID_SESION}/ventas",
        json=cuerpo,
        headers=_cabeceras("empleado"),
    )

    assert respuesta.status_code == 400
