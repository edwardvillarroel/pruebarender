"""Smoke test de TODAS las rutas contra PostgreSQL.

Objetivo: encontrar 500s. Una ruta que Andaba en Oracle y ahora revienta es
justo lo que R3/R4 rompio sin que se notara. Se hit'ean todas las rutas con IDs
reales sacados de la data migrada, con sesion simulada via headers del gateway.

Rutas que ya raisean NotImplementedError en el repo (cotizaciones, ai/) se
esperan en 501: no son regresion.
"""
from __future__ import annotations

import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

os.environ["DB_BACKEND"] = "postgres"
os.environ["DATABASE_URL"] = os.environ.get(
    "API_TEST_DSN", "postgresql://app:app@localhost:5432/print3d_dev"
)
os.environ.setdefault("STARKEN_MODO_SIMULACION", "1")

from app import create_app  # noqa: E402
from app.infrastructure.database.connection import db  # noqa: E402
from app.infrastructure.database.models.carrito_model import CarritoItemModel  # noqa: E402
from app.infrastructure.database.models.pedido_model import PedidoModel  # noqa: E402
from app.infrastructure.database.models.producto_model import ProductoModel  # noqa: E402
from app.infrastructure.database.models.usuario_model import UsuarioModel  # noqa: E402
from app.infrastructure.database.models.venta_local_model import (  # noqa: E402
    SesionVentaModel,
)

app = create_app()

with app.app_context():
    producto = ProductoModel.query.filter_by(activo=True).first()
    producto_con_foto = ProductoModel.query.filter(
        ProductoModel.imagen_bytes.isnot(None)).first()
    usuario = UsuarioModel.query.filter_by(activo=True).first()
    admin = UsuarioModel.query.filter_by(rol="admin").first() or usuario
    pedido = PedidoModel.query.first()
    sesion = SesionVentaModel.query.first()
    color = None
    with_color = ProductoModel.query.first()
    ids = {
        "producto": str(producto.id) if producto else None,
        "con_foto": str(producto_con_foto.id) if producto_con_foto else None,
        "pedido": str(pedido.id) if pedido else None,
        "sesion": str(sesion.id) if sesion else None,
        "inexistente": "00000000-0000-0000-0000-000000000000",
    }
    roles = {
        "cliente": {"X-User-Id": str(usuario.id), "X-User-Rol": usuario.rol},
        "admin": {"X-User-Id": str(admin.id), "X-User-Rol": "admin"},
    }
    print("IDs reales de la data migrada:", ids)
    print()

ESPERADOS_501 = ("/api/cotizaciones", "/api/ai/")

fallos: list[tuple] = []
info: list[tuple] = []


def probar(metodo, ruta, headers, etiqueta=""):
    c = app.test_client()
    r = getattr(c, metodo.lower())(ruta, headers=headers, json={} if metodo == "POST" else None)
    return r


def check(nombre, r, esperar_501=False, esperar=None):
    codigo = r.status_code
    if esperar_501:
        ok = codigo == 501
        nota = "NotImplementedError (esperado)"
    elif esperar is not None:
        ok = codigo == esperar
        nota = f"se esperaba {esperar}"
    else:
        ok = 200 <= codigo < 400
        nota = ""
    if not ok:
        cuerpo = r.get_data(as_text=True)[:220].replace("\n", " ")
        print(f"  [FAIL] {nombre:52} {codigo}  {cuerpo}")
        fallos.append((nombre, codigo, cuerpo))
    else:
        print(f"  [OK  ] {nombre:52} {codigo}  {nota}")
    return ok


print("catalogo (cliente)")
check("GET /api/productos", probar("GET", "/api/productos", roles["cliente"]))
check("GET /api/categorias", probar("GET", "/api/categorias", roles["cliente"]))
check("GET /api/productos/<id>", probar("GET", f"/api/productos/{ids['producto']}", roles["cliente"]))
check("GET /api/productos/<id>/colores", probar("GET", f"/api/productos/{ids['producto']}/colores", roles["cliente"]))
# imagen/thumb se prueban con un producto que SI tenga BLOB: la API responde 404
# para los que no tienen, y eso es comportamiento correcto, no una regresion.
check("GET /api/productos/<id>/imagen (con BLOB)",
      probar("GET", f"/api/productos/{ids['con_foto']}/imagen", roles["cliente"]))
check("GET /api/productos/<id>/thumb (con BLOB)",
      probar("GET", f"/api/productos/{ids['con_foto']}/thumb", roles["cliente"]))

print("\ncarrito (cliente)")
check("GET /api/cart", probar("GET", "/api/cart", roles["cliente"]))
# POST con payload vacio debe dar 400 de validacion, no 500
check("POST /api/cart/items sin payload -> 400",
      probar("POST", "/api/cart/items", roles["cliente"]), esperar=400)

print("\npedidos (cliente y admin)")
check("GET /api/pedidos", probar("GET", "/api/pedidos", roles["cliente"]))
check("GET /api/pedidos/admin", probar("GET", "/api/pedidos/admin", roles["admin"]))
if ids["pedido"]:
    check("GET /api/pedidos/<id>", probar("GET", f"/api/pedidos/{ids['pedido']}", roles["admin"]))
    # El pedido migrado no tiene codigo de seguimiento: 400 es la respuesta
    # correcta del caso de uso, no una regresion de la migracion.
    r = probar("GET", f"/api/pedidos/{ids['pedido']}/seguimiento", roles["admin"])
    cuerpo = (r.get_json() or {})
    if "código de seguimiento" in str(cuerpo.get("mensaje", "")):
        check("GET /pedidos/<id>/seguimiento sin codigo -> 400", r, esperar=400)
    else:
        check("GET /pedidos/<id>/seguimiento", r)
else:
    print("  [skip] no hay pedidos migrados")

print("\nventas locales (admin)")
# Estas rutas son POST. Se hit'ean contra un UUID inexistente para probar que
# la ruta resuelve y llega al repositorio (400 "Sesion no encontrada" del caso
# de uso) SIN crear data de prueba.
check("GET /api/ventas/sesiones/actual", probar("GET", "/api/ventas/sesiones/actual", roles["admin"]))
check("POST /api/ventas/sesiones/<uuid>/ventas (uuid inexistente)",
      probar("POST", f"/api/ventas/sesiones/{ids['inexistente']}/ventas", roles["admin"]),
      esperar=400)
check("POST /api/ventas/sesiones/<uuid>/cierre (uuid inexistente)",
      probar("POST", f"/api/ventas/sesiones/{ids['inexistente']}/cierre", roles["admin"]),
      esperar=400)
if ids["sesion"]:
    check("GET /api/ventas/reportes/<id>", probar("GET", f"/api/ventas/reportes/{ids['sesion']}", roles["admin"]))
else:
    print("  [skip] no hay sesiones de venta migradas")
check("GET /api/ventas/reportes", probar("GET", "/api/ventas/reportes", roles["admin"]))

print("\nrutas ya NotImplementedError en el repo (deben seguir en 501)")
check("GET /api/cotizaciones", probar("GET", "/api/cotizaciones", roles["admin"]), esperar_501=True)
check("GET /api/ai/image-to-3d/<id>", probar("GET", "/api/ai/image-to-3d/x", roles["admin"]), esperar_501=True)

print()
if fallos:
    print(f"RESULTADO: {len(fallos)} rutas con fallo")
    for nombre, codigo, cuerpo in fallos:
        print(f"  - {nombre}: {codigo}")
        if codigo == 500:
            print(f"      {cuerpo}")
    sys.exit(1)
print("RESULTADO: ninguna ruta revienta contra PostgreSQL")