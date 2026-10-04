"""Prueba de ESCRITURA contra PostgreSQL: ciclo completo de venta local.

Aqui esta el riesgo real de la migracion, no en los GET. El descuento de stock
de `venta_local_repository.registrar_venta` es un `UPDATE ... WHERE stock >=
cantidad` con guarda por `rowcount`: si ese rowcount no llega bien desde
psycopg2, el guard no dispara y se puede vender stock inexistente (oversell) o
rechazar ventas validas.

Cubre: abrir sesion -> vender (descuenta) -> oversell (409 y NO descuenta) ->
cerrar (reporte con totales) -> limpiar.
"""
from __future__ import annotations

import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

os.environ["DB_BACKEND"] = "postgres"
os.environ["DATABASE_URL"] = os.environ.get(
    "VENTAS_TEST_DSN", "postgresql://app:app@localhost:5432/print3d_dev"
)

from app import create_app  # noqa: E402
from app.infrastructure.database.connection import db  # noqa: E402
from app.infrastructure.database.models.producto_model import ProductoModel  # noqa: E402
from app.infrastructure.database.models.usuario_model import UsuarioModel  # noqa: E402

app = create_app()
c = app.test_client()

fallos: list[str] = []
notas: list[str] = []


def check(nombre, cond, detalle=""):
    print(f"  [{'OK ' if cond else 'FAIL'}] {nombre}{'  ' + str(detalle) if detalle else ''}")
    if not cond:
        fallos.append(nombre)
    return cond


def stock_de(pid):
    with app.app_context():
        db.session.expire_all()
        m = db.session.get(ProductoModel, pid)
        return int(m.stock) if m else None


# --- datos reales de la data migrada ---
with app.app_context():
    admin = UsuarioModel.query.filter_by(rol="admin", activo=True).first()
    producto = (
        ProductoModel.query.filter_by(activo=True).filter(ProductoModel.stock > 0).first()
    )
    admin_id, prod_id = admin.id, producto.id
    stock_inicial = int(producto.stock)
    precio = int(producto.precio)
    nombre_prod = producto.nombre

H = {"X-User-Id": str(admin_id), "X-User-Rol": "admin"}
CANT = 1
notas.append(f"producto={nombre_prod!r} stock={stock_inicial} precio={precio}")

print("1. abrir sesion de venta")
r = c.post("/api/ventas/sesiones", json={"lugar": "Prueba R4"}, headers=H)
check("POST /api/ventas/sesiones responde 201", r.status_code == 201,
      f"{r.status_code} {r.get_data(as_text=True)[:150]}")
sesion_id = (r.get_json() or {}).get("sesion", {}).get("id")
check("  devuelve id de sesion", bool(sesion_id), sesion_id)
if not sesion_id:
    print("ABORTANDO: no hay sesion")
    sys.exit(1)

print("\n2. registrar venta (debe descontar stock)")
r = c.post(f"/api/ventas/sesiones/{sesion_id}/ventas",
           json={"medio_pago": "efectivo",
                 "items": [{"producto_id": str(prod_id), "cantidad": CANT}]},
           headers=H)
check("POST .../ventas responde 201", r.status_code == 201,
      f"{r.status_code} {r.get_data(as_text=True)[:150]}")
venta = (r.get_json() or {}).get("venta", {})
check("  total = precio x cantidad", venta.get("total") == precio * CANT,
      f"total={venta.get('total')} esperado={precio * CANT}")
check("  medio_pago persistido", venta.get("medio_pago") == "efectivo", venta.get("medio_pago"))
check("  items persistidos con snapshot de nombre", bool(venta.get("items"))
      and venta["items"][0].get("nombre") == nombre_prod,
      (venta.get("items") or [{}])[0].get("nombre"))
check("  subtotal calculado por la ruta",
      bool(venta.get("items")) and venta["items"][0].get("subtotal") == precio * CANT)

stock_tras_venta = stock_de(prod_id)
check("  el stock se descontó en la BD", stock_tras_venta == stock_inicial - CANT,
      f"{stock_inicial} -> {stock_tras_venta}")

print("\n3. oversell: pedir mas de lo que hay debe 409 y NO tocar el stock")
r = c.post(f"/api/ventas/sesiones/{sesion_id}/ventas",
           json={"medio_pago": "efectivo",
                 "items": [{"producto_id": str(prod_id),
                            "cantidad": stock_tras_venta + 50}]},
           headers=H)
check("responde 409 (conflicto de stock)", r.status_code == 409,
      f"{r.status_code} {r.get_data(as_text=True)[:150]}")
check("  el mensaje menciona stock", "stock" in (r.get_json() or {}).get("mensaje", "").lower(),
      (r.get_json() or {}).get("mensaje"))
stock_tras_oversell = stock_de(prod_id)
check("  el stock NO se movio (rollback del guard atomico)",
      stock_tras_oversell == stock_tras_venta, f"{stock_tras_venta} -> {stock_tras_oversell}")

print("\n4. validaciones de la ruta")
r = c.post(f"/api/ventas/sesiones/{sesion_id}/ventas",
           json={"medio_pago": "bitcoin", "items": [{"producto_id": str(prod_id), "cantidad": 1}]},
           headers=H)
check("medio de pago invalido -> 400", r.status_code == 400, r.status_code)
r = c.post(f"/api/ventas/sesiones/{sesion_id}/ventas",
           json={"medio_pago": "efectivo", "items": []}, headers=H)
check("sin items -> 400", r.status_code == 400, r.status_code)
r = c.post("/api/ventas/sesiones", json={"lugar": "X"}, headers={"X-User-Id": str(admin_id), "X-User-Rol": "cliente"})
check("no admin no puede abrir sesion -> 403", r.status_code == 403, r.status_code)

print("\n5. cerrar sesion y leer el reporte")
r = c.post(f"/api/ventas/sesiones/{sesion_id}/cierre", json={}, headers=H)
check("POST .../cierre responde 200", r.status_code == 200,
      f"{r.status_code} {r.get_data(as_text=True)[:150]}")
rep = (r.get_json() or {}).get("reporte", {})
check("  estado cerrada", rep.get("estado") == "cerrada", rep.get("estado"))
check("  cerrada_en informada", bool(rep.get("cerrada_en")), rep.get("cerrada_en"))
check("  n_ventas=1", rep.get("n_ventas") == 1, rep.get("n_ventas"))
check("  total acumulado", rep.get("total") == precio * CANT, rep.get("total"))
check("  total_efectivo = total", rep.get("total_efectivo") == precio * CANT, rep.get("total_efectivo"))
check("  total_tuu = 0", rep.get("total_tuu") == 0, rep.get("total_tuu"))

r = c.get(f"/api/ventas/reportes/{sesion_id}", headers=H)
check("GET /api/ventas/reportes/<id> responde 200", r.status_code == 200, r.status_code)
check("  el reporte persistido conserva el total",
      ((r.get_json() or {}).get("reporte") or {}).get("total") == precio * CANT)

r = c.post(f"/api/ventas/sesiones/{sesion_id}/cierre", json={}, headers=H)
check("cerrar dos veces -> 409", r.status_code == 409, r.status_code)

print("\n6. limpiar los datos de prueba y restaurar el stock")
with app.app_context():
    from sqlalchemy import text
    with db.session.begin():
        db.session.execute(text("DELETE FROM venta_local_items WHERE venta_id IN "
                                "(SELECT id FROM ventas_local WHERE sesion_id = :s)"),
                           {"s": str(sesion_id)})
        db.session.execute(text("DELETE FROM ventas_local WHERE sesion_id = :s"),
                           {"s": str(sesion_id)})
        db.session.execute(text("DELETE FROM sesiones_venta WHERE id = :s"),
                           {"s": str(sesion_id)})
        db.session.execute(text("UPDATE productos SET stock = :s WHERE id = :p"),
                           {"s": stock_inicial, "p": str(prod_id)})
final = stock_de(prod_id)
check("stock restaurado al valor migrado", final == stock_inicial, f"{stock_inicial} vs {final}")

print()
for n in notas:
    print(f"  nota: {n}")
print()
if fallos:
    print(f"RESULTADO: {len(fallos)} FALLARON -> {fallos}")
    sys.exit(1)
print("RESULTADO: el ciclo de venta local (con descuento atomico de stock) funciona en PostgreSQL")