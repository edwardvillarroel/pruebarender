





from __future__ import annotations

import decimal

from flask.json.provider import DefaultJSONProvider
from flask.json.provider import _default as _default_flask


def _default(o):
    if isinstance(o, decimal.Decimal):
        numero = float(o)
        return int(numero) if numero.is_integer() else numero
    return _default_flask(o)


class ProveedorJsonApp(DefaultJSONProvider):
    default = staticmethod(_default)