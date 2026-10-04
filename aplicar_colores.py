"""Aplica migrations/crear_producto_colores.sql a la BD configurada en .env.

Equivalente a correr el .sql con sqlplus, pero usando la misma conexion de la
app. Es idempotente: se puede volver a ejecutar sin romper nada.

Uso:  .venv\\Scripts\\python.exe aplicar_colores.py
"""
import os
import re
import sys

BASE = r"C:\Users\jonca\ApoloVibes"
sys.path.insert(0, BASE)
os.chdir(BASE)

from app import create_app
from app.infrastructure.database.connection import db

SQL = open(os.path.join(BASE, "migrations", "crear_producto_colores.sql"), encoding="utf-8").read()


def bloques(sql: str):
    """Parte el archivo en bloques PL/SQL terminados en `/`."""
    partes = re.split(r"/\s*\n", sql)
    for p in partes:
        p = re.sub(r"--[^\n]*", "", p).strip()
        if p:
            yield p


app = create_app()
with app.app_context():
    for i, bloque in enumerate(bloques(SQL), 1):
        try:
            db.session.execute(db.text(bloque))
            db.session.commit()
            print(f"[OK]   bloque {i}")
        except Exception as e:
            db.session.rollback()
            msg = str(e).split("\n")[0]
            print(f"[FALLA] bloque {i}: {msg}")

    # Verificacion
    from sqlalchemy import text

    for consulta, etiqueta in [
        ("SELECT COUNT(*) FROM user_tables WHERE table_name='PRODUCTO_COLORES'", "tabla producto_colores"),
        ("SELECT COUNT(*) FROM user_tab_columns WHERE table_name='CARRITO_ITEMS' AND column_name='COLOR'", "carrito_items.color"),
        ("SELECT COUNT(*) FROM user_tab_columns WHERE table_name='DETALLE_PEDIDOS' AND column_name='COLOR'", "detalle_pedidos.color"),
    ]:
        n = db.session.execute(text(consulta)).scalar_one()
        print(f"{'EXISTE' if n else 'FALTA '} {etiqueta}")

    cols = db.session.execute(
        text("SELECT column_name FROM user_tab_columns WHERE table_name='PRODUCTO_COLORES' ORDER BY column_id")
    ).scalars().all()
    print("columnas:", cols)
