"""Proveedor JSON que serializa `Decimal` como numero, no como texto.

Por que existe
--------------
`DefaultJSONProvider` de Flask resuelve en una sola linea el caso de `Decimal`:

    if isinstance(o, (decimal.Decimal, uuid.UUID)):
        return str(o)

Es decir, todo `numeric` de Postgres sale como string JSON. Con Oracle,
`NUMBER(10,2)` volvia como numero plano y el frontend recibia numeros; al
migrar a Postgres, `numeric` devuelve `Decimal` de psycopg2 y cada columna
numerica empezo a viajar como texto.

El dano es silencioso y aparece en el render, no en los tests. En JS los
strings no tienen `toLocaleString`, asi que `precio.toLocaleString('es-CL')`
ignora el locale y devuelve el texto crudo: `$7140.00` en vez de `$7.140`.
Y con `+` es peor, porque concatena: un `reduce` de cantidad arrancando en
`0` daba `"011"` para dos items de cantidad 1.

Arreglarlo campo por campo en cada serializer es fragil y ya se demostro
que fuga: se escaparon `stock`, `rating` y `cantidad`. Un provider los mata a
todos y cubre las columnas numericas que se agreguen manana.
"""

from __future__ import annotations

import decimal

from flask.json.provider import DefaultJSONProvider
from flask.json.provider import _default as _default_flask


def _default(o):
    if isinstance(o, decimal.Decimal):
        # Pesos enteros salen como `int` (`7140`, no `7140.0`) para no
        # ensuciar el payload; si hay centavos conserva el `float`.
        numero = float(o)
        return int(numero) if numero.is_integer() else numero
    # `date`, `UUID`, dataclasses y `Markup` los resuelve Flask como siempre.
    # `UUID -> str` es INTOCABLE: la API depende de eso en `id`,
    # `categoria_id` y `usuario_id`.
    return _default_flask(o)


class ProveedorJsonApp(DefaultJSONProvider):
    default = staticmethod(_default)