



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

    def crear_intento(self, solicitud):
        raise AssertionError("no se deberia abrir un intento en estos tests")

    def verificar_firma(self, parametros):
        return True


@pytest.fixture
def descuento_stock():


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
    return db.session.execute(
        db.text("SELECT stock FROM productos WHERE id = :i"), {"i": producto_id}
    ).scalar_one()


def _aviso(producto_id) -> bool:
    return db.session.execute(
        db.text("SELECT aviso_stock_enviado FROM productos WHERE id = :i"),
        {"i": producto_id},
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
    p = producto(stock=1)
    descuento_stock()._descontar_stock(_pedido_con((p.id, 1)))
    assert _stock(p.id) == 0


def test_descuento_es_todo_o_nada_por_pedido(descuento_stock, producto):

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
    p = producto(stock=5)
    with pytest.raises(ValueError):
        descuento_stock()._descontar_stock(_pedido_con((p.id, -3)))
    assert _stock(p.id) == 5, "una cantidad negativa aumentó el stock"


def test_descontar_stock_es_atomico_entre_hilos(app, categoria, centinela):

    with app.app_context():
        nuevo = ProductoModel(
            categoria_id=categoria.id,
            nombre=f"{centinela}-carrera",
            precio=1000,
            stock=1,
        )
        db.session.add(nuevo)
        db.session.commit()
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




def test_descontar_por_debajo_del_umbral_global_marca_el_aviso(descuento_stock, producto):
    p = producto(stock=5)
    descuento_stock()._descontar_stock(_pedido_con((p.id, 2)))
    assert _stock(p.id) == 3
    assert _aviso(p.id) is True, (
        "el cruce de 5 a 3 (<= STOCK_BAJO=3) tiene que marcar el aviso"
    )


def test_descontar_sin_cruzar_el_umbral_no_marca_el_aviso(descuento_stock, producto):
    p = producto(stock=10)
    descuento_stock()._descontar_stock(_pedido_con((p.id, 2)))
    assert _stock(p.id) == 8
    assert _aviso(p.id) is False


def test_si_ya_estaba_bajo_el_aviso_no_se_vuelve_a_marcar(descuento_stock, producto):
    p = producto(stock=2)
    descuento_stock()._descontar_stock(_pedido_con((p.id, 1)))
    assert _stock(p.id) == 1
    assert _aviso(p.id) is False, (
        "ya estaba bajo el umbral antes de descontar: no es un cruce"
    )


def test_el_stock_minimo_propio_desplaza_al_global(descuento_stock, producto):
    p = producto(stock=6, stock_minimo=5)
    descuento_stock()._descontar_stock(_pedido_con((p.id, 2)))
    assert _stock(p.id) == 4
    assert _aviso(p.id) is True, (
        "cruzó 6 -> 4 (<= stock_minimo=5): el umbral propio manda sobre el global"
    )


def test_el_aviso_se_marca_una_sola_vez_y_no_se_apaga_con_descuentos_posteriores(
    descuento_stock, producto
):
    p = producto(stock=10, stock_minimo=3)
    descuento_stock()._descontar_stock(_pedido_con((p.id, 1)))
    assert _aviso(p.id) is False

    descuento_stock()._descontar_stock(_pedido_con((p.id, 6)))
    assert _stock(p.id) == 3
    assert _aviso(p.id) is True

    descuento_stock()._descontar_stock(_pedido_con((p.id, 1)))
    assert _aviso(p.id) is True, "ya marcado: otro descuento no lo apaga"