import os
from contextlib import contextmanager

import oracledb

_pool = None

def _parametros_oracle():
    usuario = os.getenv("ORACLE_USER", "ADMIN")
    password = os.getenv("ORACLE_PASSWORD", "")
    dsn = os.getenv("ORACLE_DSN", "")
    wallet = os.getenv("ORACLE_WALLET_DIR", "")
    return usuario, password, dsn, wallet

def _kwargs_pool():
    _, _, _, wallet = _parametros_oracle()
    kwargs = {}
    if wallet :
        kwargs["wallet_location"] = wallet
        kwargs["config_dir"] = wallet
        wallet_password = os.getenv("ORACLE_WALLET_PASSWORD", "")
        if wallet_password:
            kwargs["wallet_password"] = wallet_password
    return kwargs

def obtener_pool() -> oracledb.ConnectionPool | None:
    global _pool
    if _pool is None:
        usuario, password, dsn, _ = _parametros_oracle()
        if not dsn:
            return None
        # `timeout` es cuanto espera `acquire()` una conexion libre. El default de
        # oracledb son 30s: un pool agotado se quedaba colgado en silencio media
        # minuto y el error llegaba tarde y sin contexto. Con 5s revienta rapido
        # con DPY-4010, que dice exactamente "pool agotado".
        timeout_pool = float(os.getenv("ORACLE_POOL_TIMEOUT", "5"))
        _pool = oracledb.ConnectionPool(
            user=usuario,
            password=password,
            dsn=dsn,
            min=1,
            max=10,
            increment=1,
            timeout=timeout_pool,
            **_kwargs_pool(),
        )
    return _pool

@contextmanager
def adquirir_conexion():
    pool = obtener_pool()
    if pool is None:
        raise RuntimeError("Oracle no configurado: falta ORACLE_DSN")   
    conexion = pool.acquire()
    try:
        yield conexion
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        pool.release(conexion)