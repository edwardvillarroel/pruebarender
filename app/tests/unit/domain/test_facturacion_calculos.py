





from __future__ import annotations

import pytest

from app.domain.facturacion import (
    ajustar_ultima_linea,
    calcular_montos,
    netos_unitarios,
    redondear,
)




def test_redondeo_comercial_lleva_el_cinco_hacia_arriba():

    assert redondear(0.5) == 1
    assert redondear(1.5) == 2
    assert redondear(2.5) == 3


def test_redondeo_trunca_la_restante():
    assert redondear(2.4) == 2
    assert redondear(2.6) == 3




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

    for total in range(1, 5000, 7):
        neto, iva = calcular_montos(total)
        assert neto + iva == total, f"el total {total} quedo en {neto + iva}"


def test_el_iva_no_se_aparta_mas_de_un_peso_del_19_por_ciento():

    for total in range(1, 5000, 13):
        neto, iva = calcular_montos(total)
        canonico = round(neto * 0.19)
        assert abs(iva - canonico) <= 1, f"total {total}: iva {iva} vs {canonico}"


def test_el_neto_es_el_mas_cercano_al_total_sin_iva():
    assert calcular_montos(1000)[0] == 840
    assert calcular_montos(1190)[0] == 1000
    assert calcular_montos(9520)[0] == 8000




def test_neto_unitario_redondea_cada_precio():

    assert netos_unitarios([60]) == [50]
    assert netos_unitarios([100]) == [84]
    assert netos_unitarios([1190]) == [1000]


def test_neto_unitario_de_un_precio_exacto():
    assert netos_unitarios([11900]) == [10000]
    assert netos_unitarios([23800]) == [20000]




def test_ajusta_la_ultima_linea_cuando_falta():
    assert ajustar_ultima_linea([500, 500], 1001) == [500, 501]


def test_no_ajusta_si_ya_cuadra():
    assert ajustar_ultima_linea([500, 500], 1000) == [500, 500]


def test_ajusta_tambien_a_la_baja():
    assert ajustar_ultima_linea([500, 501], 1000) == [500, 500]


def test_no_toca_las_lineas_anteriores():
    ajustadas = ajustar_ultima_linea([100, 200, 300], 601)
    assert ajustadas[:2] == [100, 200]
    assert ajustadas[2] == 301


def test_lista_vacia_no_revienta():
    assert ajustar_ultima_linea([], 100) == []
