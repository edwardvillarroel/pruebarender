


from __future__ import annotations

from datetime import timedelta

import pytest

from app.infrastructure.database.connection import db
from app.infrastructure.database.models.detalle_pedido_model import DetallePedidoModel
from app.infrastructure.database.models.pago_model import PagoModel
from app.infrastructure.database.models.pedido_model import PedidoModel
from app.domain.time import utcnow


def _pedido(usuario, total: int = 1000) -> PedidoModel:
    p = PedidoModel(
        usuario_id=usuario.id,
        total=total,
        entrega="retiro",
        estado="pendiente",
    )
    db.session.add(p)
    db.session.commit()
    return p


def _linea(pedido, producto, cantidad: int, precio_unitario: int) -> DetallePedidoModel:
    linea = DetallePedidoModel(
        pedido_id=pedido.id,
        producto_id=producto.id,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
        nombre=producto.nombre,
    )
    db.session.add(linea)
    db.session.commit()
    return linea


def _pago(pedido, estado: str, creado_en=None) -> PagoModel:
    pago = PagoModel(
        pedido_id=pedido.id,
        monto=pedido.total,
        proveedor="tuu",
        estado=estado,
    )
    if creado_en is not None:
        pago.creado_en = creado_en
    db.session.add(pago)
    db.session.commit()
    return pago


def _compra(usuario, producto, cantidad: int, precio_unitario: int, estado: str = "completado"):
    pedido = _pedido(usuario, total=cantidad * precio_unitario)
    _linea(pedido, producto, cantidad, precio_unitario)
    _pago(pedido, estado)
    return pedido


def _ranking(client, query: str = "") -> dict:
    respuesta = client.get(f"/api/productos/mas-vendidos{query}")
    assert respuesta.status_code == 200, respuesta.get_json()
    return respuesta.get_json()


def _por_id(cuerpo: dict) -> dict:
    return {p["id"]: p for p in cuerpo["productos"]}




def test_el_ranking_cuenta_las_unidades_vendidas(client, producto, usuario, centinela):
    p = producto(stock=10, nombre=f"{centinela}-vendido", precio=5000)
    _compra(usuario, p, 3, 5000)

    cuerpo = _ranking(client)

    assert str(p.id) in _por_id(cuerpo)
    assert _por_id(cuerpo)[str(p.id)]["unidades_vendidas"] == 3


def test_el_ranking_suma_las_unidades_de_varias_compras(client, producto, usuario, centinela):
    p = producto(stock=10, nombre=f"{centinela}-repetido", precio=5000)
    _compra(usuario, p, 2, 5000)
    _compra(usuario, p, 5, 5000)

    cuerpo = _ranking(client)

    assert _por_id(cuerpo)[str(p.id)]["unidades_vendidas"] == 7


def test_los_ingresos_suman_el_precio_del_momento_de_la_compra(client, producto, usuario, centinela):
    p = producto(stock=10, nombre=f"{centinela}-ingresos", precio=5000)
    _compra(usuario, p, 4, 5000)

    cuerpo = _ranking(client)

    assert _por_id(cuerpo)[str(p.id)]["ingresos"] == 20000




def test_el_ranking_no_cuenta_un_pedido_sin_pago(client, producto, usuario, centinela):
    p = producto(stock=10, nombre=f"{centinela}-abandonado", precio=5000)
    _compra(usuario, p, 3, 5000, estado="pendiente")

    cuerpo = _ranking(client)

    assert str(p.id) not in _por_id(cuerpo)


def test_el_ranking_no_cuenta_un_pago_fallido(client, producto, usuario, centinela):
    p = producto(stock=10, nombre=f"{centinela}-fallido", precio=5000)
    _compra(usuario, p, 3, 5000, estado="fallido")

    cuerpo = _ranking(client)

    assert str(p.id) not in _por_id(cuerpo)


def test_un_pedido_con_varios_pagos_no_infla_las_unidades(client, producto, usuario, centinela):

    p = producto(stock=10, nombre=f"{centinela}-reintento", precio=5000)
    pedido = _pedido(usuario, total=10000)
    _linea(pedido, p, 2, 5000)
    _pago(pedido, "fallido")
    _pago(pedido, "completado")

    cuerpo = _ranking(client)

    assert _por_id(cuerpo)[str(p.id)]["unidades_vendidas"] == 2


def test_un_producto_dado_de_baja_no_entra_al_ranking(client, producto, usuario, centinela, db_sesion):
    p = producto(stock=10, nombre=f"{centinela}-inactivo", precio=5000)
    _compra(usuario, p, 9, 5000)
    p.activo = False
    db_sesion.commit()

    cuerpo = _ranking(client)

    assert str(p.id) not in _por_id(cuerpo)




def test_el_ranking_ordena_por_unidades_vendidas(client, producto, usuario, centinela):
    mucho = producto(stock=10, nombre=f"{centinela}-mucho", precio=5000)
    poco = producto(stock=10, nombre=f"{centinela}-poco", precio=5000)
    _compra(usuario, mucho, 9, 5000)
    _compra(usuario, poco, 2, 5000)

    cuerpo = _ranking(client)

    mios = [
        p["id"]
        for p in cuerpo["productos"]
        if p["id"] in {str(mucho.id), str(poco.id)}
    ]
    assert mios == [str(mucho.id), str(poco.id)]


def test_la_ventana_de_venta_excluye_lo_vendido_antes(client, producto, usuario, centinela):
    p = producto(stock=10, nombre=f"{centinela}-viejo", precio=5000)
    pedido = _pedido(usuario, total=5000)
    _linea(pedido, p, 3, 5000)
    _pago(pedido, "completado", creado_en=utcnow() - timedelta(days=40))

    assert str(p.id) not in _por_id(_ranking(client, "?periodo=30d"))
    assert str(p.id) in _por_id(_ranking(client, "?periodo=todo"))


def test_lo_vendido_dentro_de_la_ventana_entra(client, producto, usuario, centinela):
    p = producto(stock=10, nombre=f"{centinela}-reciente", precio=5000)
    pedido = _pedido(usuario, total=5000)
    _linea(pedido, p, 3, 5000)
    _pago(pedido, "completado", creado_en=utcnow() - timedelta(days=2))

    assert str(p.id) in _por_id(_ranking(client, "?periodo=7d"))


def test_el_limite_recorta_el_ranking(client, producto, usuario, centinela):
    for i in range(3):
        p = producto(stock=10, nombre=f"{centinela}-prod-{i}", precio=5000)
        _compra(usuario, p, 10 - i, 5000)

    cuerpo = _ranking(client, "?limite=2")

    assert len(cuerpo["productos"]) == 2
    assert cuerpo["total"] == 2




def test_el_ranking_es_publico(client, producto, usuario, centinela):
    p = producto(stock=10, nombre=f"{centinela}-publico", precio=5000)
    _compra(usuario, p, 1, 5000)

    respuesta = client.get("/api/productos/mas-vendidos")

    assert respuesta.status_code == 200
    assert str(p.id) in _por_id(respuesta.get_json())


def test_un_periodo_invalido_devuelve_400(client, producto, usuario, centinela):
    respuesta = client.get("/api/productos/mas-vendidos?periodo=7-semanas")

    assert respuesta.status_code == 400
    assert respuesta.get_json()["mensaje"]
