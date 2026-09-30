"""Ejecuta la migracion de `nuevo_lanzamiento` sobre Oracle.

Mismo patron que `_run_migration.py`: `create_app()` + `db.text()`, con
`ORA-01430` (columna ya existe) tratado como SKIP para que sea idempotente, y
verificacion final con `inspect`.

Va antes de agregar la columna al modelo ORM a proposito: si el modelo pide
`nuevo_lanzamiento` y la columna no existe, cada SELECT de productos falla con
ORA-00904 y se cae el catalogo entero.
"""
from sqlalchemy import inspect

from app import create_app
from app.infrastructure.database.connection import db

app = create_app()
with app.app_context():
    stmts = [
        "ALTER TABLE PRODUCTOS ADD (NUEVO_LANZAMIENTO NUMBER(1) DEFAULT 0 NOT NULL)",
    ]
    for stmt in stmts:
        try:
            db.session.execute(db.text(stmt))
            db.session.commit()
            print(f"OK: {stmt}")
        except Exception as e:
            db.session.rollback()
            err = str(e)
            if "ORA-01430" in err:  # column already exists
                print(f"SKIP (ya existe): {stmt}")
            else:
                print(f"ERROR: {stmt} -> {e}")

    inspector = inspect(db.engine)
    cols = {c["name"]: str(c["type"]) for c in inspector.get_columns("productos")}
    print("\nColumnas de productos:", sorted(cols))
    print("nuevo_lanzamiento ->", cols.get("NUEVO_LANZAMIENTO", "*** NO ESTA ***"))

    # Verificar que el backfill dejo las filas existentes en 0 y no en NULL.
    try:
        from sqlalchemy import text

        total, nuevos = db.session.execute(
            text("SELECT COUNT(*), COUNT(NUEVO_LANZAMIENTO) FROM PRODUCTOS")
        ).one()
        print(f"filas={total}, con flag=1: {nuevos} (esperado 0)")
    except Exception as e:
        print(f"no se pudo verificar el conteo: {e}")
