



from __future__ import annotations

import pytest

from app.infrastructure.database.connection import db
from app.infrastructure.database.models.pago_model import PagoModel
from app.infrastructure.database.models.pedido_model import PedidoModel
from app.infrastructure.database.models.usuario_model import UsuarioModel


@pytest.fixture
def admin(db_sesion, centinela):


    u = UsuarioModel(
        email=f"{centinela}-admin@caracterizacion.test",
        password_hash="r0-no-se-usa",
        nombre="R0 Caracterizacion",
        apellido="Admin",
        rol="admin",
    )
    db_sesion.add(u)
    db_sesion.commit()
    return u


def _cabeceras_admin(admin) -> dict:
    return {"X-User-Id": str(admin.id), "X-User-Rol": "admin"}


def _pedido(usuario, centinela: str, sufijo: str) -> PedidoModel:
    p = PedidoModel(
        usuario_id=usuario.id,
        total=1000,
        entrega="retiro",
        estado="pendiente",
    )
    db.session.add(p)
    db.session.commit()
    return p


def _pago(pedido: PedidoModel, estado: str) -> PagoModel:
    pago = PagoModel(
        pedido_id=pedido.id,
        monto=pedido.total,
        proveedor="tuu",
        estado=estado,
    )
    db.session.add(pago)
    db.session.commit()
    return pago


def _ids_del_panel(client, cabeceras) -> set[str]:
    respuesta = client.get("/api/pedidos/admin", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.get_json()
    return {p["id"] for p in respuesta.get_json()["pedidos"]}


def test_panel_muestra_pedidos_con_pago_completado(client, usuario, centinela, admin):
    p = _pedido(usuario, centinela, "pagado")
    _pago(p, "completado")
    pid = str(p.id)

    assert pid in _ids_del_panel(client, _cabeceras_admin(admin))


def test_panel_excluye_pedido_sin_pago(client, usuario, centinela, admin):
    p = _pedido(usuario, centinela, "abandonado")

    assert str(p.id) not in _ids_del_panel(client, _cabeceras_admin(admin))


def test_panel_excluye_pago_pendiente_y_fallido(client, usuario, centinela, admin):
    pendiente = _pedido(usuario, centinela, "pendiente")
    _pago(pendiente, "pendiente")
    fallido = _pedido(usuario, centinela, "fallido")
    _pago(fallido, "fallido")

    panel = _ids_del_panel(client, _cabeceras_admin(admin))
    assert str(pendiente.id) not in panel, "un pago sin completar no es una compra"
    assert str(fallido.id) not in panel, "un pago fallido no es una compra"


def test_no_duplica_pedidos_con_varios_pagos(client, usuario, centinela, admin):

    p = _pedido(usuario, centinela, "reintento")
    _pago(p, "fallido")
    _pago(p, "completado")
    pid = str(p.id)

    respuesta = client.get("/api/pedidos/admin", headers=_cabeceras_admin(admin))
    assert respuesta.status_code == 200, respuesta.get_json()
    ids = [ped["id"] for ped in respuesta.get_json()["pedidos"]]

    assert ids.count(pid) == 1, (
        f"el pedido aparece {ids.count(pid)} veces en el panel: "
        "una compra es una fila, sin importar cuantos intentos de pago tenga"
    )


def test_cliente_no_puede_ver_el_panel(client, usuario, centinela, admin):
    p = _pedido(usuario, centinela, "ajeno")
    _pago(p, "completado")

    respuesta = client.get(
        "/api/pedidos/admin",
        headers={"X-User-Id": str(usuario.id), "X-User-Rol": "cliente"},
    )

    assert respuesta.status_code == 403, respuesta.get_json()


def test_panel_ignora_pedidos_de_otros_usuarios(client, usuario, centinela, admin):
    propio = _pedido(usuario, centinela, "propio")
    _pago(propio, "completado")

    panel = _ids_del_panel(client, _cabeceras_admin(admin))

    assert str(propio.id) in panel, "el admin tiene que ver la compra de su cliente"