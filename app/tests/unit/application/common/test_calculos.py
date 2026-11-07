"""El total a cobrar es el precio que el cliente vio. Sin IVA encima.

Este archivo existe por un bug concreto. `productos.precio` YA incluye IVA: el
admin escribe el neto, `GestionarProducto.crear` lo guarda con IVA (10000 ->
11900) y el frontend rotula "IVA incluido" en el catalogo, en el carrito y en
los terminos. `calculos.py` era el unico lugar del sistema que multiplicaba por
1.19 otra vez, asi que cada pedido online se cobraba un 19% mas caro que lo que
el cliente tenia en pantalla: un carrito de 9.520 terminaba en 11.329.

Los tests de integracion no lo habrian detectado: ninguno asertaba el total, y
cuando se escribio WU6 el numero 13078 quedo copiado en un comentario sin que
nadie lo contrastara contra el checkout. Por eso el invariante va aca, con
nombre de test explicito.

La regla que hay que preservar:

    total = subtotal + envio

Y NO `subtotal * 1.19`. Si alguna vez hay que aplicar IVA de nuevo, el lugar
correcto es `productos.precio` (dejandola sin incluir), no este modulo.

Sobre el envio
--------------
`calcular_envio` devuelve SIEMPRE 0: el costo de envio lo paga el cliente
directamente a la empresa de transporte (asi lo rotula el checkout, que muestra
"Por calcular", y asi lo decidio el cambio que dejo `calcular_envio` en cero).
Los assertions de envio fijan ese contrato: si un dia la vuelve a cobrar la
tienda, este archivo tiene que cambiar a la par con el frontend.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.application.common.calculos import (
    ENVIO_GRATIS_DESDE,
    calcular_envio,
    calcular_total_con_envio,
)


# --------------------------------------------------------------------------
# calcular_envio: la tienda no cobra envio
# --------------------------------------------------------------------------


def test_retiro_no_cobra_envio():
    assert calcular_envio(1000, "retiro") == 0


def test_envio_tampoco_cobra_desde_la_tienda():
    """El envio lo paga el cliente al transportista: la tienda cobra 0."""
    assert calcular_envio(1000, "envio") == 0


def test_entrega_desconocida_tampoco_cobra_envio():
    """Una entrega que no es 'retiro' se trata como envio: sigue costando 0.

    El checkout solo ofrece 'retiro' y 'envio', asi que hoy es inaccesible. Se
    deja fijado el comportamiento para que, si alguna vez llega un valor raro,
    nadie descubra que cobro de mas.
    """
    assert calcular_envio(1000, None) == 0
    assert calcular_envio(1000, "lo-que-sea") == 0


def test_el_umbral_de_envio_gratis_sigue_en_50000():
    """Contrato con el frontend: el banner de "envio gratis" usa este numero."""
    assert ENVIO_GRATIS_DESDE == 50000


# --------------------------------------------------------------------------
# calcular_total_con_envio: el invariante
# --------------------------------------------------------------------------


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
    """Regresion del 19%: el total tiene que ser EXACTAMENTE subtotal + envio.

    El nombre del test es el documento. Este caso particular fue 11.329 contra
    9.520 en los tres pedidos de prueba, o sea lo que la pagina le mostraba al
    cliente contra lo que se le cobro de verdad.
    """
    subtotal = 9520
    total = calcular_total_con_envio(subtotal, "retiro")

    assert total == 9520, (
        f"el total quedo en {total}: se le volvio a aplicar IVA a un precio que "
        "ya la incluye, y el cliente paga mas de lo que vio"
    )
    assert total != round(subtotal * 1.19)


def test_el_total_coincide_con_lo_que_muestra_el_carrito():
    """El invariante escrito en la moneda del checkout.

    El frontend hace `total + costoEnvio` (hoy costoEnvio = 0, "Por calcular")
    y desglosa `total / 1.19` solo para mostrar la base. Si el backend no hace
    exactamente lo mismo, el total esperado que manda el cliente nunca coincide
    y los pagos dan 409: ese fue el sintoma que destapo este bug cuando se
    activo la validacion de WU6.
    """
    subtotal, envio = 5000, calcular_envio(5000, "envio")
    del_backend = calcular_total_con_envio(subtotal, "envio")
    del_checkout = subtotal + envio

    assert del_backend == del_checkout == 5000


def test_envio_gratis_no_altera_el_subtotal():
    """Sobre el umbral el total es el subtotal pelado, no el subtotal con IVA."""
    assert calcular_total_con_envio(60000, "envio") == 60000


# --------------------------------------------------------------------------
# El total tiene que ser un int, no un Decimal
# --------------------------------------------------------------------------


def test_el_total_es_int_aunque_llegue_un_decimal_de_postgres():
    """`productos.precio` es `numeric(10,2)`, asi que Postgres da `Decimal`.

    Si el total se escapa como `Decimal` revienta en `TuuCliente.crear_intento`,
    que manda el payload con el `json.dumps` de la stdlib y no serializa
    `Decimal`. Ese error es el sintoma de este bug; la causa es que el calculo
    devuelve el tipo de la columna en vez de un entero de pesos.
    """
    total = calcular_total_con_envio(Decimal("9520.00"), "retiro")

    assert isinstance(total, int), f"el total salio como {type(total).__name__}"
    assert total == 9520


def test_el_envio_tambien_sale_int_desde_un_decimal():
    """`calcular_envio` devuelve un `int`, que no filtre `Decimal`."""
    envio = calcular_envio(Decimal("1000.50"), "envio")

    assert isinstance(envio, int)
    assert envio == 0


def test_un_decimal_en_el_umbral_no_paga_envio():
    """El umbral se compara bien aunque el subtotal venga con decimales."""
    assert calcular_total_con_envio(Decimal("50000.00"), "envio") == 50000
    assert calcular_envio(Decimal("49999.99"), "envio") == 0
