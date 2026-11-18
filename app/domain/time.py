

from __future__ import annotations

import datetime as dt

try:  # pragma: no cover - depende de la base de datos de zonas del sistema
    from zoneinfo import ZoneInfo

    ZONA_CHILE = ZoneInfo("America/Santiago")
except Exception:  # pragma: no cover
    ZONA_CHILE = dt.timezone(dt.timedelta(hours=-4))


def utcnow() -> dt.datetime:

    return dt.datetime.now(dt.timezone.utc)


def hoy_chile() -> dt.date:

    return dt.datetime.now(ZONA_CHILE).date()
