"""Caracterizacion del pago con pasarela y, sobre todo, del descuento de stock.

El invariante que estos tests congelan es que la confirmacion de un pago NUNCA
puede vender stock que no existe, y que el descuento de un pedido es
todo-o-nada. Son las dos cosas que un leer-modificar-escribir en Python rompe:
dos pagos concurrentes leen el mismo stock y los dos lo descuentan, y un pedido
con varios productos descuenta el primero y falla en el segundo dejando stock
derivando para un pedido que la pasarela va a rechazar.

`test_descontar_stock_es_atomico_entre_hilos` es el que importa: no simula la
carrera, la provoca. Dos hilos con su propia sesion y su propio contexto de app
disputan la ultima unidad; exactamente uno puede ganar. Si el descuento volviera
a ser "leer, comparar en Python, escribir", los dos pasarian y el test falla.

Nota sobre `match=`: fragmentos cortos y ASCII a proposito, para que el test se
rompa por un cambio real de comportamiento y no por el encoding del archivo.
"""

from __future__ import annotations

import threading
import uuid

import pytest

from app.application.pedidos_pagos.procesar_pago import ProcesarPago
from app.domain.entities.detalle_pedido import DetallePedido
from app.domain.entities.pedido import Pedido
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.producto_model import ProductoModel
from app.infrastructure.repositories.producto_repository import ProductoRepository


class _PasarelaFalsa:
    """Pasarela que no hace nada: estos tests no ejercitan la pasarela."""

    def crear_intento(self, solicitud):
        raise AssertionError("no se deberia abrir un intento en estos tests")

    def verificar_firma(self, parametros):
        return True


@pytest.fixture
def descuento_stock():
    """ProcesarPago armado solo para el descuento de stock.

    `_descontar_stock` es el unico punto donde el pago muta stock y no toca la
    pasarela ni los repos de pedido/pago/carrito, asi que no hace falta
    cablearlos y el test queda centrado en la invariante de stock.
    """

    def _instancia() -> ProcesarPago:
        return ProcesarPago(
            pedidos=None,
            pagos=None,
            productos=ProductoRepository(),
            pasarela=_PasarelaFalsa(),
            carritos=None,
        )

    return _instancia


def _pedido_con(*pares) -> Pedido:
    """Pedido en memoria con los `(producto_id, cantidad)` indicados.

    No hace falta persistirlo: `_descontar_stock` solo recorre `pedido.detalles`.
    """
    pedido = Pedido(usuario_id=uuid.uuid4())
    for producto_id, cantidad in pares:
        pedido.detalles.append(
            DetallePedido(
                pedido_id=pedido.id,
                producto_id=producto_id,
                cantidad=cantidad,
                precio_unitario=1000,
            )
        )
    return pedido


def _stock(producto_id) -> int:
    """Stock leido fresco de la base, no de la sesion cacheada de SQLAlchemy."""
    return db.session.execute(
        db.text("SELECT stock FROM productos WHERE id = :i"), {"i": producto_id}
    ).scalar_one()


def test_confirmacion_descuenta_stock(descuento_stock, producto):
    p = producto(stock=10)
    descuento_stock()._descontar_stock(_pedido_con((p.id, 3)))
    assert _stock(p.id) == 7, "el stock no se descontó"


def test_no_se_puede_confirmar_si_no_alcanza(descuento_stock, producto):
    p = producto(stock=1)
    with pytest.raises(ValueError):
        descuento_stock()._descontar_stock(_pedido_con((p.id, 5)))
    assert _stock(p.id) == 1, "un pago rechazado no puede tocar el stock"


def test_stock_queda_exacto_en_cero(descuento_stock, producto):
    """Vender la ultima unidad deja 0, nunca negativo."""
    p = producto(stock=1)
    descuento_stock()._descontar_stock(_pedido_con((p.id, 1)))
    assert _stock(p.id) == 0


def test_descuento_es_todo_o_nada_por_pedido(descuento_stock, producto):
    """Si un producto del pedido no alcanza, no se descuenta ninguno.

    El primero tiene stock de sobra y el segundo no. Un descuento item por item
    dejaria al primero descontado para un pedido que despues se rechaza.
    """
    con_stock = producto(stock=10, nombre="r0-primero-con-stock")
    sin_stock = producto(stock=0, nombre="r0-segundo-sin-stock")

    with pytest.raises(ValueError):
        descuento_stock()._descontar_stock(
            _pedido_con((con_stock.id, 2), (sin_stock.id, 1))
        )

    assert _stock(con_stock.id) == 10, (
        "el primer producto se descontó aunque el pedido completo no pudo "
        "confirmarse: el descuento tiene que ser todo-o-nada"
    )
    assert _stock(sin_stock.id) == 0


def test_cantidad_cero_o_negativa_no_aumenta_stock(descuento_stock, producto):
    """Un payload con cantidad negativa no puede convertirse en stock gratis."""
    p = producto(stock=5)
    with pytest.raises(ValueError):
        descuento_stock()._descontar_stock(_pedido_con((p.id, -3)))
    assert _stock(p.id) == 5, "una cantidad negativa aumentó el stock"


def test_descontar_stock_es_atomico_entre_hilos(app, categoria, centinela):
    """La carrera real: dos pagos disputan la ultima unidad.

    Cada hilo corre su propio contexto de app y su propia sesion, que es como
    se comportan dos peticiones simultaneas en produccion. La barrera los obliga
    a intentar el descuento al mismo tiempo, en vez de que uno termine antes de
    que el otro empiece.
    """
    with app.app_context():
        nuevo = ProductoModel(
            categoria_id=categoria.id,
            nombre=f"{centinela}-carrera",
            precio=1000,
            stock=1,
        )
        db.session.add(nuevo)
        db.session.commit()
        # El id se copia antes de soltar la sesion: despues el objeto ORM queda
        # desasociado y leer `nuevo.id` revienta con DetachedInstanceError.
        producto_id = nuevo.id
        db.session.remove()

    barrera = threading.Barrier(2)
    resultados: list[bool] = []
    candado = threading.Lock()

    def _intentar():
        with app.app_context():
            barrera.wait(timeout=15)
            ok = ProductoRepository().descontar_stock([(producto_id, 1)])
            with candado:
                resultados.append(ok)

    hilos = [threading.Thread(target=_intentar) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=30)

    assert len(resultados) == 2, f"un hilo no terminó: {resultados}"
    assert resultados.count(True) == 1, (
        f"exactamente un pago debía ganar la última unidad, pero los resultados "
        f"fueron {resultados}: el descuento no es atómico"
    )

    with app.app_context():
        assert _stock(producto_id) == 0, (
            "el stock quedó en negativo o no llegó a 0: se vendió más de lo que había"
        )