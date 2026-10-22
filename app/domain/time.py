"""Instantes de tiempo del dominio, siempre con zona horaria.

Vive en `domain` (no en `infrastructure`) porque lo necesitan tanto las entidades
puras como los modelos ORM, y `domain` no puede importar de `infrastructure`.
Definirlo aca evita que cada capa tenga su propia copia.
"""

from __future__ import annotations

import datetime as dt

try:  # pragma: no cover - depende de la base de datos de zonas del sistema
    from zoneinfo import ZoneInfo

    ZONA_CHILE = ZoneInfo("America/Santiago")
except Exception:  # pragma: no cover
    ZONA_CHILE = dt.timezone(dt.timedelta(hours=-4))


def utcnow() -> dt.datetime:
    """Instante actual en UTC, con `tzinfo`.

    `datetime.utcnow()` devuelve un instante NAIVE. Contra una columna
    `timestamptz`, PostgreSQL reinterpreta el valor en el `TimeZone` de la
    sesion, asi que lo guardado depende de como este configurado el servidor.
    Ademas, `psycopg2` SI devuelve datetimes con `tzinfo` al leer un
    `timestamptz`, asi que un default naive se mixuraria con los valores leidos y
    compararlos lanza `TypeError: can't compare offset-naive and offset-aware
    datetimes`. Por eso todo el codigo usa este helper.
    """
    return dt.datetime.now(dt.timezone.utc)


def hoy_chile() -> dt.date:
    """Fecha de hoy en hora de Chile.

    La fecha de emisión del documento (`FchEmis`) es la fecha local de Chile,
    no la del servidor: un servidor en UTC cerca de medianoche pondría el día
    equivocado en el comprobante.
    """
    return dt.datetime.now(ZONA_CHILE).date()
