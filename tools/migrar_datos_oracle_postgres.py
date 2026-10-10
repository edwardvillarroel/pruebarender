"""R2: migra los datos de Oracle Autonomous a PostgreSQL.

Conversión tipo-driven: lee los tipos de las columnas destino desde
`information_schema` y convierte en función de eso, en lugar de hardcodear
una tabla de conversiones por columna. Si el schema destino cambia, el script
sigue siendo correcto.

Uso:
    python tools/migrar_datos_oracle_postgres.py --truncate
    python tools/migrar_datos_oracle_postgres.py --dry-run
    python tools/migrar_datos_oracle_postgres.py --tabla productos --tabla carrito_items

Solo escribe en el destino. Nunca escribe en Oracle.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import pathlib
import sys
import time
import uuid

REPO = pathlib.Path(__file__).resolve().parent.parent
DUMP = pathlib.Path(r"C:\Users\jonca\AppData\Local\Temp\opencode\ddl_oracle")


def load_dotenv(path: pathlib.Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_dotenv(REPO / ".env")

import oracledb  # noqa: E402
import psycopg2  # noqa: E402
import psycopg2.extras  # noqa: E402

# LOBs: 28 MB en total, entra de sobra. Sin esto los LOB devuelven un locator
# inusable y el fetch falla.
oracledb.defaults.fetch_lobs = True

UTC = dt.timezone.utc


# --------------------------------------------------------------------------
# conexion
# --------------------------------------------------------------------------
def conectar_oracle():
    kw = {}
    wallet = os.environ.get("ORACLE_WALLET_DIR", "")
    if wallet:
        kw["config_dir"] = wallet
        kw["wallet_location"] = wallet
    wp = os.environ.get("ORACLE_WALLET_PASSWORD", "")
    if wp:
        kw["wallet_password"] = wp
    return oracledb.connect(
        user=os.environ.get("ORACLE_USER", "ADMIN"),
        password=os.environ.get("ORACLE_PASSWORD", ""),
        dsn=os.environ.get("ORACLE_DSN", ""),
        **kw,
    )


def conectar_pg():
    """Conexion al destino.

    Prioriza `DATABASE_URL` / `PG_DSN`, igual que el gateway (`pg_pool._dsn`),
    y recien ahi cae a los `POSTGRES_*` sueltos. Antes solo leia `POSTGRES_*` con
    defaults a localhost: si la app estaba configurada con `DATABASE_URL` para
    Supabase y el `.env` no traia `POSTGRES_HOST`, este script cargaba en el
    Postgres local sin decir nada. El destino tiene que ser una sola verdad.
    """
    dsn = os.getenv("DATABASE_URL") or os.getenv("PG_DSN")
    if dsn:
        return psycopg2.connect(dsn, connect_timeout=int(os.getenv("PG_CONNECT_TIMEOUT", "30")))
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "print3d_migracion"),
        user=os.getenv("POSTGRES_USER", "app"),
        password=os.getenv("POSTGRES_PASSWORD", "app"),
    )


# --------------------------------------------------------------------------
# schema destino
# --------------------------------------------------------------------------
def columnas_destino(pg) -> dict[str, dict[str, str]]:
    """{tabla: {columna: data_type}} leyendo el schema ya migrado."""
    cur = pg.cursor()
    cur.execute(
        """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        """
    )
    tablas: dict[str, dict[str, str]] = {}
    for t, c, dtp in cur.fetchall():
        tablas.setdefault(t, {})[c] = dtp
    cur.close()
    return tablas


def orden_por_fk(pg) -> list[str]:
    """Orden topologico: los padres antes que los hijos, para no violar FKs."""
    cur = pg.cursor()
    cur.execute(
        """
        SELECT c.conrelid::regclass::text AS hijo,
               c.confrelid::regclass::text AS padre
        FROM pg_constraint c
        WHERE c.contype = 'f' AND c.connamespace = 'public'::regnamespace
        """
    )
    aristas = cur.fetchall()
    cur.close()

    tablas = list(columnas_destino(pg))
    deps = {t: set() for t in tablas}
    for hijo, padre in aristas:
        hijo, padre = hijo.split(".")[-1].strip('"'), padre.split(".")[-1].strip('"')
        if hijo in deps and padre in deps and padre != hijo:
            deps[hijo].add(padre)

    orden, pendientes = [], set(tablas)
    while pendientes:
        # Todos los padres tienen que estar YA emitidos. Con `&` en vez de `<=`,
        # en la primera ronda el conjunto esta vacio y las tablas con FK se
        # marcan listas antes que su padre.
        listos = sorted(t for t in pendientes if deps[t] <= set(orden))
        if not listos:  # ciclo: no deberia pasar, pero no colgarse
            sys.exit(f"CICLO de FK entre tablas: {sorted(pendientes)}")
        orden.extend(listos)
        pendientes -= set(listos)
    return orden


# --------------------------------------------------------------------------
# conversion
# --------------------------------------------------------------------------
def hacer_conversor(data_type: str):
    """Devuelve f(valor_oracle) -> valor_postgres para el tipo destino dado."""
    if data_type == "uuid":
        def _uuid(v):
            if v is None:
                return None
            if isinstance(v, bytes):
                return str(uuid.UUID(bytes=v))
            return str(uuid.UUID(str(v)))
        return _uuid

    if data_type == "boolean":
        # Oracle NUMBER(1,0) sin CHECK de dominio: 0 falso, todo lo demas true.
        return lambda v: None if v is None else bool(int(v))

    if data_type == "bytea":
        def _bytea(v):
            if v is None:
                return None
            if isinstance(v, oracledb.LOB):
                v = v.read()
            return psycopg2.Binary(v)
        return _bytea

    if data_type in ("text", "character varying", "character"):
        def _texto(v):
            if v is None:
                return None
            if isinstance(v, oracledb.LOB):
                return v.read()
            return v
        return _texto

    if data_type == "timestamp with time zone":
        def _tstz(v):
            if v is None:
                return None
            if isinstance(v, dt.datetime) and v.tzinfo is None:
                # Oracle guarda TIMESTAMP sin zona como hora de pared. El
                # servidor de Autonomous corre en UTC, asi que se asume UTC y
                # se cuenta para poder auditarlo.
                return v.replace(tzinfo=UTC)
            return v
        return _tstz

    return lambda v: v


def construir_conversores(pg, tabla: str) -> list:
    cols = columnas_destino(pg)[tabla]
    return {c: hacer_conversor(t) for c, t in cols.items()}


# --------------------------------------------------------------------------
# migracion
# --------------------------------------------------------------------------
def vaciar(pg, tablas: list[str]) -> None:
    cur = pg.cursor()
    cur.execute("TRUNCATE TABLE " + ", ".join(f'"{t}"' for t in tablas)
                + " RESTART IDENTITY CASCADE")
    pg.commit()
    print(f"destino vaciado ({len(tablas)} tablas)")
    cur.close()


def migrar_tabla(ora, pg, tabla: str, lote: int, dry_run: bool) -> tuple[int, int]:
    cur_o = ora.cursor()
    # Oracle guardo los nombres sin comillas, o sea en MAYUSCULAS. El
    # schema destino quedo en minusculas, asi que se traduce al vuelo.
    cur_o.execute(f'SELECT * FROM "{tabla.upper()}"')
    nombres = [d[0].lower() for d in cur_o.description]

    conv = construir_conversores(pg, tabla)
    faltan = [c for c in nombres if c not in conv]
    if faltan:
        raise KeyError(f"{tabla}: columnas Oracle sin destino: {faltan}")
    extra = [c for c in conv if c not in nombres]
    if extra:
        raise KeyError(f"{tabla}: columnas destino sin origen Oracle: {extra}")

    filas = 0
    buffer: list[tuple] = []
    while True:
        lote_filas = cur_o.fetchmany(lote)
        if not lote_filas:
            break
        for fila in lote_filas:
            buffer.append(tuple(conv[c](v) for c, v in zip(nombres, fila)))
        filas += len(lote_filas)

    if dry_run:
        print(f"  {tabla:24} {filas:>8} filas (dry-run, no escritas)")
        return filas, 0

    cur_p = pg.cursor()
    sql = (f'INSERT INTO "{tabla}" '
           f'({", ".join(chr(34) + c + chr(34) for c in nombres)}) '
           f'VALUES %s')
    psycopg2.extras.execute_values(cur_p, sql, buffer, page_size=1000)
    pg.commit()
    cur_p.close()
    print(f"  {tabla:24} {filas:>8} filas")
    return filas, len(buffer)


def sincronizar_sequences(pg) -> None:
    """Reseña las secuencias de las columnas IDENTITY.

    El migrador inserta los `id` explicitos que traia Oracle, y PostgreSQL NO
    avanza la secuencia al insertar un valor explicito. Sin esto, el primer
    INSERT que genere una identidad choca contra una fila ya migrada:
    `duplicate key value violates unique constraint ..._pkey`.
    """
    cur = pg.cursor()
    cur.execute(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND is_identity = 'YES'
        ORDER BY table_name
        """
    )
    for tabla, columna in cur.fetchall():
        cur.execute(
            "SELECT setval(pg_get_serial_sequence(%s, %s), "
            "COALESCE((SELECT MAX(" + columna + ") FROM " + tabla + "), 1), "
            "(SELECT MAX(" + columna + ") FROM " + tabla + ") IS NOT NULL)",
            (tabla, columna),
        )
        valor = cur.fetchone()[0]
        print(f"  secuencia resincronizada: {tabla}.{columna} -> {valor}")
    pg.commit()
    cur.close()


# Nombres de base que se consideran de descarte. `--truncate` hace
# `TRUNCATE ... RESTART IDENTITY CASCADE` sobre TODAS las tablas: si apunta por
# error a la base real, la destruye sin margen de recuperacion. Por eso el
# destino tiene que declararse descartable por nombre.
BASES_DISCARDABLES = ("test", "dev", "tmp", "temp", "discard", "scratch", "sandbox")


def exigir_destino_descartable(pg, Forzar: bool) -> str:
    """Falla si la base de destino no es evidentemente de pruebas.

    Antes de correr `--truncate` contra una base productive (por ejemplo la de
    Supabase) hay que pasar `--i-destroy-target` a proposito. No es friccion
    para el uso normal: los nombres de desarrollo y test pasan siempre.
    """
    params = pg.get_dsn_parameters()
    dbname = params.get("dbname") or ""
    host = params.get("host") or ""

    if Forzar:
        print(f"ATENCION: --i-destroy-target activo, se trunca {dbname}@{host}\n")
        return dbname

    if any(marca in dbname.lower() for marca in BASES_DISCARDABLES):
        return dbname

    sys.exit(
        "ABORTADO: no se trunca una base que no sea descartable.\n"
        f"  destino: {dbname}@{host}\n"
        f"  permitidas por nombre: {', '.join(BASES_DISCARDABLES)}\n"
        "  Para migrar de verdad hacia una base productive, el flujo correcto es\n"
        "  dejar el destino vacio de origen (base recien creada) y correr SIN\n"
        "  --truncate. Si estas seguro de querer vaciar esta base:\n"
        "    --truncate --i-destroy-target"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--truncate", action="store_true", help="vacia el destino antes de migrar")
    ap.add_argument("--i-destroy-target", action="store_true",
                    help="confirma que la base de destino se puede vaciar")
    ap.add_argument("--dry-run", action="store_true", help="solo lee y cuenta, no escribe")
    ap.add_argument("--lote", type=int, default=500)
    ap.add_argument("--tabla", action="append", default=[], help="limita a estas tablas")
    args = ap.parse_args()

    ora = conectar_oracle()
    pg = conectar_pg()
    print(f"Oracle OK | Postgres OK ({pg.get_dsn_parameters()['dbname']})\n")

    tablas = columnas_destino(pg)
    if not tablas:
        sys.exit("el destino no tiene tablas: aplicar antes migrations/postgres/schema_completo.sql")

    if args.tabla:
        faltantes = [t for t in args.tabla if t not in tablas]
        if faltantes:
            sys.exit(f"tablas inexistentes en destino: {faltantes}")
        orden = [t for t in orden_por_fk(pg) if t in args.tabla]
    else:
        orden = orden_por_fk(pg)

    if args.truncate and not args.dry_run:
        exigir_destino_descartable(pg, args.i_destroy_target)
        vaciar(pg, orden)

    print("orden de carga (padres -> hijos):")
    print("  " + " -> ".join(orden) + "\n")

    t0 = time.time()
    total = 0
    resumen = []
    for tabla in orden:
        filas, _ = migrar_tabla(ora, pg, tabla, args.lote, args.dry_run)
        total += filas
        resumen.append((tabla, filas))

    dt_s = time.time() - t0
    if not args.dry_run:
        print("\nresincronizando secuencias IDENTITY:")
        sincronizar_sequences(pg)
    print(f"\n{'tabla':24} {'filas':>10}")
    for t, n in sorted(resumen, key=lambda x: -x[1]):
        print(f"{t:24} {n:>10}")
    print(f"\nTOTAL {total} filas en {dt_s:.1f}s")

    # verificacion: el conteo de Postgres tiene que coincidir con el de Oracle
    if not args.dry_run:
        print("\nverificacion de conteos:")
        cur = pg.cursor()
        malas = 0
        for tabla, esperadas in resumen:
            cur.execute(f'SELECT count(*) FROM "{tabla}"')
            obtenidas = cur.fetchone()[0]
            ok = obtenidas == esperadas
            malas += 0 if ok else 1
            if not ok:
                print(f"  DESCUADRE {tabla}: oracle={esperadas} postgres={obtenidas}")
        cur.close()
        print("  todos los conteos coinciden" if not malas
              else f"  {malas} tablas con descuadre")
        if malas:
            return 1

    ora.close()
    pg.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())