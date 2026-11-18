



from __future__ import annotations

import pytest

from app.api.routes.pedido_routes import _clave_idempotencia, _entero_opcional




@pytest.mark.parametrize(
    "crudo,esperado",
    [
        (13078, 13078),
        ("13078", 13078),
        ("  13078  ", 13078),
        ("1", 1),
    ],
)
def test_entero_opcional_acepta_lo_que_es_un_entero(crudo, esperado):
    assert _entero_opcional(crudo) == esperado


@pytest.mark.parametrize(
    "basura",
    [
        None,
        "",
        "   ",
        "abc",
        "13.078",
        "13078.5",
        {},
        [],
        object(),
        13078.0,
    ],
)
def test_entero_opcional_descarta_lo_que_no_es_entero(basura):
    assert _entero_opcional(basura) is None


@pytest.mark.parametrize("falso", [True, False, 0, -1, -13078])
def test_entero_opcional_descarta_los_no_positivos(falso):


    assert _entero_opcional(falso) is None




@pytest.mark.parametrize(
    "crudo",
    [
        "abc-123",
        "ABC_123",
        "9f8a7b6c-5d4e-4f3a-9b2c-1d0e9f8a7b6c",
        "a",
        "a" * 100,
    ],
)
def test_clave_idempotencia_acepta_la_lista_blanca(crudo):
    assert _clave_idempotencia(crudo) == crudo


def test_clave_idempotencia_normaliza_el_espacio_sobrante():
    assert _clave_idempotencia("  abc-123  ") == "abc-123"


@pytest.mark.parametrize(
    "malo",
    [
        "",
        "   ",
        "a" * 101,
        "clave con espacios",
        "clave/../otra",
        "clave; DROP TABLE pagos;--",
        "clave.con.puntos",
        "clave\u0000nulo",
        "clave\nnueva",
        "clave\ttab",
    ],
)
def test_clave_idempotencia_descarta_lo_que_no_cumple_la_lista_blanca(malo):

    assert _clave_idempotencia(malo) is None


@pytest.mark.parametrize("no_string", [None, 12345, 1.5, True, [], {}, ["abc"]])
def test_clave_idempotencia_descarta_lo_que_no_es_string(no_string):
    assert _clave_idempotencia(no_string) is None