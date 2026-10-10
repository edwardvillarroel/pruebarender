"""Los helpers que leen `totalEsperado` y `claveIdempotencia` del body.

Son la FRONTERA de WU6: lo primero que toca datos que manda el cliente, y lo
unico que separa "el cliente mando algo raro" de "el servidor revienta con un
500". No necesitan base ni app context porque son funciones puras, asi que
conviene fijarlas aqui y no solo probarlas de rebote por la API.

El criterio NO es "rechazar lo invalido" sino "descartar lo que no se puede
interpretar". Descartar tiene dos efectos que hay que tener claros:

- `total_esperado=None` desactiva la validacion del total. Preferible a fallar:
  el cliente que manda basura igual tiene el chequeo real del lado del servidor.
- `clave_idempotencia=None` desactiva la idempotencia. Es lo correcto para una
  clave con formato desconocido, porque inventar una clave propia en el
  servidor seria peor que no deduplicar: dos clics con claves distintas
  realmente crean dos pagos.
"""

from __future__ import annotations

import pytest

from app.api.routes.pedido_routes import _clave_idempotencia, _entero_opcional


# --------------------------------------------------------------------------
# _entero_opcional
# --------------------------------------------------------------------------


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
        "13.078",  # separador de miles: el frontend manda el numero plano
        "13078.5",
        {},
        [],
        object(),
        13078.0,  # un float: no se castea, se descarta. No se adivinan formatos
    ],
)
def test_entero_opcional_descarta_lo_que_no_es_entero(basura):
    assert _entero_opcional(basura) is None


@pytest.mark.parametrize("falso", [True, False, 0, -1, -13078])
def test_entero_opcional_descarta_los_no_positivos(falso):
    """Un total de pedido es siempre > 0.

    Se descartan `0` y los negativos porque son datos rotos, no un cambio de
    precio. Si llegaran a compararse, el cliente recibiria un 409 con "el total
    cambio" cuando en realidad mando basura: un mensaje que lo manda a buscar
    un problema que no tiene.

    `True` entra aca a proposito: en Python `True == 1`, y un `true` en el JSON
    no es un total aunque `int(True)` sea 1.
    """
    assert _entero_opcional(falso) is None


# --------------------------------------------------------------------------
# _clave_idempotencia
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "crudo",
    [
        "abc-123",
        "ABC_123",
        "9f8a7b6c-5d4e-4f3a-9b2c-1d0e9f8a7b6c",  # UUID, lo que genera el front
        "a",
        "a" * 100,  # el limite exacto
    ],
)
def test_clave_idempotencia_acepta_la_lista_blanca(crudo):
    assert _clave_idempotencia(crudo) == crudo


def test_clave_idempotencia_normaliza_el_espacio_sobrante():
    """Un espacio al borde es ruido del cliente, no un formato distinto."""
    assert _clave_idempotencia("  abc-123  ") == "abc-123"


@pytest.mark.parametrize(
    "malo",
    [
        "",
        "   ",  # sin espacios, `strip` lo deja vacio
        "a" * 101,  # un byte del limite
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
    """La lista blanca es solo `[A-Za-z0-9_-]` y hasta 100 caracteres.

    El filtro va en la ruta y no en el repositorio a proposito: el
    repositorio asume que ya le llega una clave limpia. Si el filtro viviera
    abajo, un `; DROP TABLE` pasaria por toda la capa de aplicación antes de
    ser rechazado en la base.
    """
    assert _clave_idempotencia(malo) is None


@pytest.mark.parametrize("no_string", [None, 12345, 1.5, True, [], {}, ["abc"]])
def test_clave_idempotencia_descarta_lo_que_no_es_string(no_string):
    """Un numero o un objeto no es una clave, aunque tenga `strip`."""
    assert _clave_idempotencia(no_string) is None