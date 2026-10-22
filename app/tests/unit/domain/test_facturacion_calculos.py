"""Los montos del documento electrónico tienen que cuadrar AL PESO.

El precio del catálogo es bruto (IVA incluido) y el comprobante dice cuál era
el total cobrado. Entre los dos hay un redondeo: el total menos su IVA no da
un entero exacto casi nunca, y el SII exige enteros.

La regla que se implementó (y que el proveedor de DTE acepta) es:

    neto = redondeo(total / 1.19)
    iva  = total - neto      <- IVA por DIFERENCIA

El IVA por diferencia puede quedar un peso arriba o abajo del 19% exacto, que
es justo la tolerancia del proveedor (verificado contra la API: acepta 189, 190
y 191, y rechaza 188 y 192). Lo que NO acepta es que el total no sea
neto + IVA.

Estos tests fijan esa aritmética porque el error típico es silencioso: el
documento se emite igual, pero al cliente le sale un comprobante que no
cuadra con lo que pagó.
"""

from __future__ import annotations

import pytest

from app.domain.facturacion import (
    ajustar_ultima_linea,
    calcular_montos,
    netos_unitarios,
    redondear,
)


# --------------------------------------------------------------------------
# redondear
# --------------------------------------------------------------------------


def test_redondeo_comercial_lleva_el_cinco_hacia_arriba():
    """El .5 exacto sube, no baja como el redondeo "al par" de Python.

    `round(0.5)` da 0 y `round(1.5)` da 2: alterna. Con pesos enteros eso
    hace que el mismo total dé dos netos distintos según el camino, y el
    comprobante no cerraría con el cobro.
    """
    assert redondear(0.5) == 1
    assert redondear(1.5) == 2
    assert redondear(2.5) == 3


def test_redondeo_trunca_la_restante():
    assert redondear(2.4) == 2
    assert redondear(2.6) == 3


# --------------------------------------------------------------------------
# calcular_montos
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "total,neto,iva",
    [
        (1000, 840, 160),
        (999, 839, 160),
        (1190, 1000, 190),
        (9520, 8000, 1520),
        (5000, 4202, 798),
        (1, 1, 0),
    ],
)
def test_montos_desglosan_el_total(total, neto, iva):
    desglose_neto, desglose_iva = calcular_montos(total)
    assert (desglose_neto, desglose_iva) == (neto, iva)


def test_neto_mas_iva_da_el_total_exacto():
    """El invariante: el documento tiene que sumar lo que se cobró.

    Con IVA canónico (redondeo del neto por 19%) el total puede quedar un peso
    arriba o abajo. Por eso el IVA va por diferencia.
    """
    for total in range(1, 5000, 7):
        neto, iva = calcular_montos(total)
        assert neto + iva == total, f"el total {total} quedo en {neto + iva}"


def test_el_iva_no_se_aparta_mas_de_un_peso_del_19_por_ciento():
    """La diferencia con el 19% exacto nunca pasa de un peso.

    Es la tolerancia que acepta el proveedor: si se pasara, el documento se
    rechaza y no hay comprobante.
    """
    for total in range(1, 5000, 13):
        neto, iva = calcular_montos(total)
        canonico = round(neto * 0.19)
        assert abs(iva - canonico) <= 1, f"total {total}: iva {iva} vs {canonico}"


def test_el_neto_es_el_mas_cercano_al_total_sin_iva():
    assert calcular_montos(1000)[0] == 840  # 840.33...
    assert calcular_montos(1190)[0] == 1000  # 1000.00 exacto
    assert calcular_montos(9520)[0] == 8000  # 8000.00 exacto


# --------------------------------------------------------------------------
# netos_unitarios
# --------------------------------------------------------------------------


def test_neto_unitario_redondea_cada_precio():
    """El precio unitario neto se redondea por unidad, no por línea.

    60 bruto son 50.42 neto: 50. Con tres unidades, el neto de la línea es
    150 y el total sigue siendo 180.
    """
    assert netos_unitarios([60]) == [50]
    assert netos_unitarios([100]) == [84]
    assert netos_unitarios([1190]) == [1000]


def test_neto_unitario_de_un_precio_exacto():
    assert netos_unitarios([11900]) == [10000]
    assert netos_unitarios([23800]) == [20000]


# --------------------------------------------------------------------------
# ajustar_ultima_linea
# --------------------------------------------------------------------------


def test_ajusta_la_ultima_linea_cuando_falta():
    """El descuadre de las líneas se absorbe en la última (regla del SII)."""
    assert ajustar_ultima_linea([500, 500], 1001) == [500, 501]


def test_no_ajusta_si_ya_cuadra():
    assert ajustar_ultima_linea([500, 500], 1000) == [500, 500]


def test_ajusta_tambien_a_la_baja():
    assert ajustar_ultima_linea([500, 501], 1000) == [500, 500]


def test_no_toca_las_lineas_anteriores():
    """Solo la última cambia: las anteriores son los precios ya cotizados."""
    ajustadas = ajustar_ultima_linea([100, 200, 300], 601)
    assert ajustadas[:2] == [100, 200]
    assert ajustadas[2] == 301


def test_lista_vacia_no_revienta():
    assert ajustar_ultima_linea([], 100) == []
