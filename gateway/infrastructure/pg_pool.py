"""Pool de conexiones PostgreSQL del gateway.

Reemplaza al pool de Oracle. Configuracion:
  - `DATABASE_URL` / `PG_DSN` (URI completa, manda si esta). En Supabase suele
    venir ya con `?sslmode=require`.
  - o variables sueltas: POSTGRES_HOST / _PORT / _DB / _USER / _PASSWORD /
    _SSLMODE.

`psycopg2` no tiene equivalente de `pool_pre_ping` de SQLAlchemy, asi que se
hace a mano: Supabase cierra las conexiones ociosas y sin esto el primer
request tras un rato de inactividad revienta con "server closed the connection".
"""

from __future__ import annotations

import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
import psycopg2.pool

# Sin esto psycopg2 no sabe adaptar objetos `uuid.UUID` y toda escritura con un
# UUID falla con "can't adapt type 'UUID'". Registra tambien el camino inverso
# (bytes -> uuid) para las lecturas.
psycopg2.extras.register_uuid()

_pool = None
_min = int(os.getenv("POSTGRES_POOL_MIN", "1"))
_max = int(os.getenv("POSTGRES_POOL_MAX", "10"))
_timeout = float(os.getenv("POSTGRES_POOL_TIMEOUT", "5"))


def _dsn():
    """Devuelve el DSN, o None si no hay configuracion de Postgres."""
    url = os.getenv("DATABASE_URL") or os.getenv("PG_DSN")
    if url:
        return url
    if not os.getenv("POSTGRES_DB"):
        return None
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
        "dbname": os.getenv("POSTGRES_DB"),
        "user": os.getenv("POSTGRES_USER", "app"),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
        "sslmode": os.getenv("POSTGRES_SSLMODE", "prefer"),
        "connect_timeout": int(os.getenv("POSTGRES_CONNECT_TIMEOUT", "10")),
    }


def obtener_pool():
    """Pool global, o None si Postgres no esta configurado (health/proxy)."""
    global _pool
    if _pool is None:
        dsn = _dsn()
        if dsn is None:
            return None
        _pool = psycopg2.pool.ThreadedConnectionPool(_min, _max, dsn)
    return _pool


def cerrar_pool():
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


def _conectar_de_nuevo(pool, conexion):
    """Reemplaza una conexion muerta por una nueva del pool."""
    pool.putconn(conexion, close=True)
    return pool.getconn()


@contextmanager
def adquirir_conexion():
    pool = obtener_pool()
    if pool is None:
        raise RuntimeError(
            "Postgres no configurado: falta DATABASE_URL o POSTGRES_DB"
        )

    conexion = pool.getconn()
    try:
        if conexion.closed:
            conexion = _conectar_de_nuevo(pool, conexion)
        else:
            # pre-ping: cheapest way to notice the server dropped an idle conn
            with conexion.cursor() as cur:
                cur.execute("SELECT 1")
            conexion.rollback()
    except Exception:
        conexion = _conectar_de_nuevo(pool, conexion)

    try:
        yield conexion
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        pool.putconn(conexion)