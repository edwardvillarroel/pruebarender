



from __future__ import annotations

import pytest

from app.application.pedidos_pagos.procesar_pago import ProcesarPago
from app.domain.interfaces.pasarela_pago import (
    PasarelaPago,
    ResultadoIntentoPago,
    SolicitudPago,
)
from app.infrastructure.repositories.carrito_repository_bd import CarritoRepositoryBd
from app.infrastructure.repositories.pago_repository import PagoRepository
from app.infrastructure.repositories.pedido_repository import PedidoRepository
from app.infrastructure.repositories.producto_repository import ProductoRepository

URL_FALSA = "https://pasarela-falsa.test/pagar"


class _PasarelaFalsa(PasarelaPago):

    def crear_intento(self, solicitud: SolicitudPago) -> ResultadoIntentoPago:
        return ResultadoIntentoPago(url=URL_FALSA, token=solicitud.referencia)

    def verificar_firma(self, parametros: dict[str, str]) -> bool:
        return True


@pytest.fixture
def pasarela_falsa(app):

    servicio = ProcesarPago(
        PedidoRepository(),
        PagoRepository(),
        ProductoRepository(),
        _PasarelaFalsa(),
        CarritoRepositoryBd(),
    )
    app.config["PAGO_SERVICE"] = servicio
    return servicio


def _cabeceras(usuario) -> dict:
    return {"X-User-Id": str(usuario.id), "X-User-Rol": "cliente"}


def _un_pedido(client, cabeceras: dict) -> dict:
    listado = client.get("/api/pedidos", headers=cabeceras)
    assert listado.status_code == 200, listado.get_json()
    pedidos = listado.get_json()["pedidos"]
    assert len(pedidos) == 1, f"se esperaba un solo pedido, hay {len(pedidos)}"
    return pedidos[0]


def test_round_trip_conserva_entrega_cliente_y_nombre_del_item(
    client, producto, usuario, centinela, pasarela_falsa
):
    p = producto(stock=10, nombre=f"{centinela}-llavero", precio=5000)
    producto_id = p.id
    cabeceras = _cabeceras(usuario)

    creado = client.post(
        "/api/pago/crear",
        json={
            "entrega": "envio",
            "cliente": {
                "nombre": "Ana",
                "apellido": "Prueba",
                "email": "ana@caracterizacion.test",
                "telefono": "+56912345678",
                "direccion": "Av. Siempre Viva 742",
            },
            "items": [{"id": str(producto_id), "cantidad": 2, "color": "Rojo"}],
        },
        headers=cabeceras,
    )
    assert creado.status_code == 200, creado.get_json()
    assert creado.get_json()["url"] == URL_FALSA, (
        f"no se abrió el intento en la pasarela falsa: {creado.get_json()!r}"
    )

    pedido = _un_pedido(client, cabeceras)

    assert pedido["entrega"] == "envio", (
        f"la entrega no se guardó: {pedido['entrega']!r}"
    )
    assert pedido["cliente"]["direccion"] == "Av. Siempre Viva 742", (
        f"el cliente no se deserializó: {pedido['cliente']!r}"
    )
    assert pedido["cliente"]["email"] == "ana@caracterizacion.test"

    assert len(pedido["items"]) == 1
    item = pedido["items"][0]
    assert item["nombre"] == f"{centinela}-llavero", (
        f"la línea no trae el snapshot del nombre: {item['nombre']!r}"
    )
    assert item["color"] == "Rojo", f"la línea no trae el color: {item['color']!r}"
    assert item["cantidad"] == 2
    assert item["precio_unitario"] == 5000


def test_nombre_del_item_es_snapshot_y_no_referencia_viva(
    client, producto, usuario, centinela, db_sesion, pasarela_falsa
):

    nombre_original = f"{centinela}-antes-del-rename"
    p = producto(stock=10, nombre=nombre_original, precio=5000)
    producto_id = p.id
    cabeceras = _cabeceras(usuario)

    creado = client.post(
        "/api/pago/crear",
        json={
            "entrega": "retiro",
            "items": [{"id": str(producto_id), "cantidad": 1}],
        },
        headers=cabeceras,
    )
    assert creado.status_code == 200, creado.get_json()

    p.nombre = f"{centinela}-despues-del-rename"
    db_sesion.commit()

    detalle = client.get(
        f"/api/pedidos/{_un_pedido(client, cabeceras)['id']}", headers=cabeceras
    )
    assert detalle.status_code == 200, detalle.get_json()
    assert detalle.get_json()["items"][0]["nombre"] == nombre_original, (
        "el nombre de la línea se resolvió contra el catálogo en vez de contra "
        "el snapshot guardado en el pedido"
    )