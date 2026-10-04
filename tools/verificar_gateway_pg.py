"""Prueba funcional del gateway contra PostgreSQL.

Ejercita los repositorios de verdad (no mocks): es la unica forma de saber que
el `ON CONFLICT` hace upsert de verdad y que los UUID/booleanos viajan bien.
Con Oraclello compilaba igual: fallaba en runtime.
"""
from __future__ import annotations

import os
import pathlib
import sys
import uuid as uuidlib

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# Antes de que nada cargue el .env: el destino es la base local migrada.
os.environ["DATABASE_URL"] = os.environ.get(
    "GATEWAY_TEST_DSN", "postgresql://app:app@localhost:5432/print3d_dev"
)

import psycopg2  # noqa: E402

from gateway.infrastructure import ddl, repositorios as R  # noqa: E402

fallos: list[str] = []


def check(nombre, condicion, detalle=""):
    print(f"  [{'OK ' if condicion else 'FAIL'}] {nombre}{'  ' + str(detalle) if detalle else ''}")
    if not condicion:
        fallos.append(nombre)


def sql(q, params=()):
    con = psycopg2.connect(os.environ["DATABASE_URL"])
    with con.cursor() as c:
        c.execute(q, params)
        filas = c.fetchall() if c.description else []
    con.commit()
    con.close()
    return filas


print("1. DDL idempotente")
ddl.crear_tablas()
ddl.crear_tablas()  # segunda vez no debe explotar
check("crear_tablas() corre dos veces sin error", True)

print("\n2. usuarios")
email = f"prueba_r3_{uuidlib.uuid4().hex[:8]}@example.com"
nuevo = R.crear_usuario(email, "hash-x", "Prueba", "R3", "+56912345678")
uid = nuevo["id"]
check("crear_usuario devuelve id", bool(uuidlib.UUID(uid)))

u = R.buscar_usuario_por_email(email)
check("buscar_usuario_por_email (case-insensitive)", u is not None)
check("  activo es booleano real", u is not None and u["activo"] is True,
      f"tipo={type(u['activo']).__name__ if u else None}")
check("  id vuelve como texto UUID", isinstance(u["id"], str))
check("buscar_usuario_por_email con otro case", R.buscar_usuario_por_email(email.upper()) is not None)

por_id = R.buscar_usuario_por_id(uid)
check("buscar_usuario_por_id (uuid nativo)", por_id is not None and por_id["id"] == uid)

R.actualizar_password(uid, "hash-nuevo")
check("actualizar_password", R.buscar_usuario_por_id(uid)["password_hash"] == "hash-nuevo")

R.actualizar_mfa(uid, "SECRETO", True)
check("actualizar_mfa deja mfa_activo=true",
      R.buscar_usuario_por_id(uid)["mfa_activo"] is True)
R.actualizar_mfa(uid, "SECRETO", False)
check("actualizar_mfa deja mfa_activo=false",
      R.buscar_usuario_por_id(uid)["mfa_activo"] is False)

print("\n3. refresh tokens")
jti = uuidlib.uuid4().hex
import datetime as dt
R.guardar_refresh(jti, uid, dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1),
                  "1.2.3.4", "pytest")
r = R.buscar_refresh(jti)
check("guardar_refresh + buscar_refresh", r is not None and r["jti"] == jti)
check("  revocado es booleano y arranca en false", r["revocado"] is False)
R.revocar_refresh(jti)
check("revocar_refresh deja revocado=true", R.buscar_refresh(jti)["revocado"] is True)
R.revocar_tokens_de_usuario(uid)
check("revocar_tokens_de_usuario", R.buscar_refresh(jti)["revocado"] is True)

print("\n4. bloqueos de login: el ON CONFLICT (venia de un MERGE)")
R.limpiar_bloqueo(email, "email")
R.guardar_o_actualizar_bloqueo(email, "email", 1, 0, None)
R.guardar_o_actualizar_bloqueo(email, "email", 2, 0, None)
R.guardar_o_actualizar_bloqueo(email, "email", 3, 1, None)
b = R.buscar_bloqueo(email, "email")
check("3 upserts dejan UNA sola fila", b is not None and b["fallos"] == 3,
      f"fallos={b['fallos'] if b else None}")
n = sql("SELECT count(*) FROM bloqueos_login WHERE LOWER(clave)=LOWER(%s)", (email,))[0][0]
check("  y no se duplicaron filas en la tabla", n == 1, f"filas={n}")

# el MERGE comparaba LOWER(clave)=LOWER(clave): el match es case-insensitive
R.limpiar_bloqueo(email, "email")
R.guardar_o_actualizar_bloqueo(email, "email", 1, 0, None)
R.guardar_o_actualizar_bloqueo(email.upper(), "email", 7, 0, None)
b = R.buscar_bloqueo(email, "email")
check("upsert case-insensitive (clave en MAYUS actualiza la de minus)",
      b is not None and b["fallos"] == 7, f"fallos={b['fallos'] if b else None}")
n = sql("SELECT count(*) FROM bloqueos_login WHERE LOWER(clave)=LOWER(%s)", (email,))[0][0]
check("  sin duplicar por diferencia de case", n == 1, f"filas={n}")

R.limpiar_bloqueo(email, "email")
check("limpiar_bloqueo", R.buscar_bloqueo(email, "email") is None)

print("\n5. codigos de verificacion")
R.guardar_codigo(email, "hash-verif", dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=10))
c = R.buscar_codigo(email)
check("guardar_codigo + buscar_codigo", c is not None and c["codigo_hash"] == "hash-verif")
check("  usado es booleano y arranca en false", c["usado"] is False)
R.marcar_codigo_usado(email)
check("marcar_codigo_usado", R.buscar_codigo(email) is None)

print("\n6. codigos de respaldo")
R.guardar_codigos_respaldo(uid, ["h1", "h2", "h3"])
cs = R.buscar_codigo_respaldo_activo(uid)
check("guardar_codigos_respaldo + buscar", len(cs) == 3, f"n={len(cs)}")
R.marcar_codigo_respaldo_usado(cs[0]["id"])
check("marcar_codigo_respaldo_usado", len(R.buscar_codigo_respaldo_activo(uid)) == 2)

print("\n7. limpieza")
sql("DELETE FROM refresh_tokens WHERE user_id=%s", (uid,))
sql("DELETE FROM codigos_respaldo WHERE user_id=%s", (uid,))
sql("DELETE FROM codigos_verificacion WHERE LOWER(email)=LOWER(%s)", (email,))
sql("DELETE FROM bloqueos_login WHERE LOWER(clave)=LOWER(%s)", (email,))
sql("DELETE FROM usuarios WHERE id=%s", (uuidlib.UUID(uid),))
check("filas de prueba eliminadas", True)

print()
if fallos:
    print(f"RESULTADO: {len(fallos)} FALLARON -> {fallos}")
    sys.exit(1)
print("RESULTADO: el gateway funciona contra PostgreSQL")