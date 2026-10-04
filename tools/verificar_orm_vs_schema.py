"""Compara los modelos ORM contra el schema real de Postgres.

Los modelos se escribieron contra Oracle y nuncaTeneron `server_default`, asi
que pueden referenciar columnas que no existen o faltar columnas que la BD si
tiene. Este diff es el que detecta eso antes de que reviente en runtime.

Uso: python tools/verificar_orm_vs_schema.py
"""
from __future__ import annotations

import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import psycopg2  # noqa: E402

# Hay que importar TODOS los modelos para que queden registrados en db.metadata.
from app.infrastructure.database.models import (  # noqa: E402,F401
    carrito_model,
    categoria_model,
    detalle_pedido_model,
    log_auditoria_model,
    notificacion_model,
    pago_model,
    pedido_model,
    producto_color_model,
    producto_model,
    solicitud_diseno_model,
    usuario_model,
    venta_local_model,
)
from app.infrastructure.database.connection import db  # noqa: E402

pg = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=os.getenv("POSTGRES_PORT", "5432"),
    dbname=os.getenv("POSTGRES_DB", "print3d_dev"),
    user=os.getenv("POSTGRES_USER", "app"),
    password=os.getenv("POSTGRES_PASSWORD", "app"),
)
cur = pg.cursor()
cur.execute(
    "SELECT table_name, column_name FROM information_schema.columns "
    "WHERE table_schema='public'"
)
bd: dict[str, set[str]] = {}
for t, c in cur.fetchall():
    bd.setdefault(t, set()).add(c)

problemas = 0
print(f"{'tabla':26} {'estado'}")
print("-" * 72)
for tabla in sorted(db.metadata.tables):
    orm = db.metadata.tables[tabla]
    cols_orm = {c.name.lower() for c in orm.columns}
    cols_bd = bd.get(tabla, set())

    if not cols_bd:
        print(f"{tabla:26} SIN TABLA EN LA BD")
        problemas += 1
        continue

    # el nombre logico de la columna (p.ej. specs_raw -> "specs")
    reales = {(c.name if not c.key else c.key) for c in orm.columns}
    logicos = {c.name.lower() for c in orm.columns}
    solo_orm = {k for k in reales if k.lower() not in cols_bd and k not in cols_bd}
    solo_bd = cols_bd - logicos - {r.lower() for r in reales}
    # columnas con server_default en BD que el ORM no declara
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=%s AND column_default IS NOT NULL",
        (tabla,),
    )
    con_default = {r[0].lower() for r in cur.fetchall()}
    faltantes = con_default - logicos - {r.lower() for r in reales}

    if solo_orm or solo_bd or faltantes:
        problemas += 1
        print(f"{tabla:26} DIFERENCIAS")
        if solo_orm:
            print(f"{'':26}   solo en ORM: {sorted(solo_orm)}")
        if solo_bd:
            print(f"{'':26}   solo en BD : {sorted(solo_bd)}")
        if faltantes:
            print(f"{'':26}   en BD con DEFAULT y ausentes del ORM: {sorted(faltantes)}")
    else:
        print(f"{tabla:26} ok ({len(logicos)} columnas)")

print("-" * 72)
extra_bd = sorted(set(bd) - set(db.metadata.tables))
if extra_bd:
    print(f"tablas en la BD sin modelo ORM: {extra_bd}")
print("OK: el ORM coincide con el schema" if not problemas
      else f"{problemas} tablas con diferencias")
sys.exit(1 if problemas else 0)