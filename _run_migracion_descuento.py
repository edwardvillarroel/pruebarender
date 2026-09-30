"""Aplica la migracion de descuento "oferta real" sobre la BD configurada.

Lee el SQL versionado de `migrations/aplicar_descuento_baja_precio.sql` y lo
ejecuta con SQLAlchemy. El UPDATE es idempotente (guardia en el WHERE), asi que
puede reejecutarse sin duplicar el descuento. Imprime antes/despues y verifica
el caso Lapras (neto 10.000 -> base 11.900 -> paga 10.710 con 10% OFF).
"""
from sqlalchemy import text

from app import create_app
from app.infrastructure.database.connection import db

app = create_app()
with app.app_context():
    antes = db.session.execute(
        text("SELECT NOMBRE, PRECIO, DESCUENTO, PRECIO_ORIGINAL FROM PRODUCTOS WHERE DESCUENTO IS NOT NULL AND DESCUENTO > 0 ORDER BY NOMBRE")
    ).all()
    print("=== Con descuento ANTES de migrar ===")
    for n, p, d, o in antes:
        print(f"  {n!r}: precio={p} desc={d} original={o}")

    sql = open("migrations/aplicar_descuento_baja_precio.sql", encoding="utf-8").read()
    resultado = db.session.execute(text(sql))
    db.session.commit()
    print(f"\nFilas actualizadas: {resultado.rowcount}")

    lapras = db.session.execute(
        text("SELECT PRECIO, DESCUENTO, PRECIO_ORIGINAL FROM PRODUCTOS WHERE UPPER(NOMBRE) LIKE '%LAPRA%'")
    ).all()
    print("\nLapras DESPUES:")
    for p, d, o in lapras:
        print(f"  precio={p} desc={d} original={o} (esperado precio=10710, original=11900)")