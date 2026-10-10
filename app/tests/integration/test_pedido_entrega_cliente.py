"""El pedido tiene que recordar cómo se pidió: entrega, cliente y nombre del producto.

Tres datos se perdían en el camino antes de WU1:

1. `entrega` ("retiro" / "envio") se usaba para calcular el total y después se
   tiraba: el pedido guardado no decía cómo iba a llegar la compra.
2. `direccion_envio` guardaba el cliente como JSON crudo y ninguna ruta lo
   deserializaba, así que el frontend no tenía con quién mostrar los datos de
   envío.
3. `detalle_pedidos` solo guardaba el `producto_id`. Si el admin renombra el
   producto, los pedidos viejos cambian de nombre solos: un pedido es un
   documento histórico y su línea tiene que decir lo que se compró ese día.

Este test es el round-trip completo: entra por la API pública (`POST
/api/pago/crear`, con pasarela falsa para no salir a la red) y sale por la API
pública (`GET /api/pedidos`), o sea atraviesa DTO, caso de uso, entidad,
repositorio, SQL y de vuelta a JSON. El punto es que el dato llegue entero, no en
qué capa se perdió.
"""

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
    """Pasarela que no hace HTTP: devuelve una URL fija y acepta cualquier firma."""

    def crear_intento(self, solicitud: SolicitudPago) -> ResultadoIntentoPago:
        return ResultadoIntentoPago(url=URL_FALSA, token=solicitud.referencia)

    def verificar_firma(self, parametros: dict[str, str]) -> bool:
        return True


@pytest.fixture
def pasarela_falsa(app):
    """Reemplaza `PAGO_SERVICE` por uno armado con la pasarela falsa.

    El punto de composición vive en `app.config`, así que alcanza con rehacer el
    `ProcesarPago` contra los repositorios reales: la escritura del pedido y del
    pago siguen yendo a la base de verdad, que es justo lo que hay que probar.
    """
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
    """El único pedido del usuario, para no repetir el `GET /api/pedidos`."""
    listado = client.get("/api/pedidos", headers=cabeceras)
    assert listado.status_code == 200, listado.get_json()
    pedidos = listado.get_json()["pedidos"]
    assert len(pedidos) == 1, f"se esperaba un solo pedido, hay {len(pedidos)}"
    return pedidos[0]


def test_round_trip_conserva_entrega_cliente_y_nombre_del_item(
    client, producto, usuario, centinela, pasarela_falsa
):
    """Compra con envío: los tres datos vuelven tal cual se mandaron."""
    p = producto(stock=10, nombre=f"{centinela}-llavero", precio=5000)
    # El id se copia antes de la petición: a partir de ahí el pedido corre con su
    # propia sesión y leerlo del objeto ORM puede reventar al desasociarse.
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

    # `/pago/crear` devuelve {url, token}, no el pedido: hay que releerlo para
    # ver qué se guardó. El listado del propio usuario alcanza porque la compra
    # recién hecha es la única que tiene.
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
    """Renombrar el producto no puede reescribir los pedidos ya hechos.

    Es la razón de guardar `nombre` además del `producto_id`: el precio ya era
    un snapshot, y un pedido que cambia de nombre solo con editar el catálogo
    deja de ser un registro fiel de lo que se compró.
    """
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