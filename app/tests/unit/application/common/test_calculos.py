






from __future__ import annotations

from decimal import Decimal

import pytest

from app.application.common.calculos import (
    ENVIO_GRATIS_DESDE,
    calcular_envio,
    calcular_total_con_envio,
)




def test_retiro_no_cobra_envio():
    assert calcular_envio(1000, "retiro") == 0


def test_envio_tampoco_cobra_desde_la_tienda():
    assert calcular_envio(1000, "envio") == 0


def test_entrega_desconocida_tampoco_cobra_envio():

    assert calcular_envio(1000, None) == 0
    assert calcular_envio(1000, "lo-que-sea") == 0


def test_el_umbral_de_envio_gratis_sigue_en_50000():
    assert ENVIO_GRATIS_DESDE == 50000




@pytest.mark.parametrize(
    "subtotal,entrega,esperado",
    [
        (9520, "retiro", 9520),
        (5000, "envio", 5000),
        (5000, "retiro", 5000),
        (ENVIO_GRATIS_DESDE, "envio", 50000),
        (ENVIO_GRATIS_DESDE + 1, "envio", 50001),
        (1, "envio", 1),
        (0, "envio", 0),
    ],
)
def test_total_es_subtotal_mas_envio(subtotal, entrega, esperado):
    assert calcular_total_con_envio(subtotal, entrega) == esperado


def test_el_total_no_se_multiplica_por_iva():

    subtotal = 9520
    total = calcular_total_con_envio(subtotal, "retiro")

    assert total == 9520, (
        f"el total quedo en {total}: se le volvio a aplicar IVA a un precio que "
        "ya la incluye, y el cliente paga mas de lo que vio"
    )
    assert total != round(subtotal * 1.19)


def test_el_total_coincide_con_lo_que_muestra_el_carrito():

    subtotal, envio = 5000, calcular_envio(5000, "envio")
    del_backend = calcular_total_con_envio(subtotal, "envio")
    del_checkout = subtotal + envio

    assert del_backend == del_checkout == 5000


def test_envio_gratis_no_altera_el_subtotal():
    assert calcular_total_con_envio(60000, "envio") == 60000




def test_el_total_es_int_aunque_llegue_un_decimal_de_postgres():

    total = calcular_total_con_envio(Decimal("9520.00"), "retiro")

    assert isinstance(total, int), f"el total salio como {type(total).__name__}"
    assert total == 9520


def test_el_envio_tambien_sale_int_desde_un_decimal():
    envio = calcular_envio(Decimal("1000.50"), "envio")

    assert isinstance(envio, int)
    assert envio == 0


def test_un_decimal_en_el_umbral_no_paga_envio():
    assert calcular_total_con_envio(Decimal("50000.00"), "envio") == 50000
    assert calcular_envio(Decimal("49999.99"), "envio") == 0
