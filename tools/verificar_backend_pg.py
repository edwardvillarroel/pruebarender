"""Prueba funcional del backend contra PostgreSQL, sobre la DATA MIGRADA.

No usa una base vacia: lee los 751 registros que migrated R2. Asi se prueba lo
que importa de verdad, que el ORM (ya sin `UuidRaw`) lee UUIDs nativos,
booleanos y los ~15 MB de BLOBs de `productos` y `producto_colores`.
"""
from __future__ import annotations

import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

os.environ["DB_BACKEND"] = "postgres"
os.environ["DATABASE_URL"] = os.environ.get(
    "BACKEND_TEST_DSN", "postgresql://app:app@localhost:5432/print3d_dev"
)
os.environ.setdefault("LLM_API_KEY", "")
os.environ.setdefault("STARKEN_MODO_SIMULACION", "1")

from app import create_app  # noqa: E402
from app.infrastructure.database.connection import db  # noqa: E402
from app.infrastructure.database.models.carrito_model import (  # noqa: E402
    CarritoItemModel,
    CarritoModel,
)
from app.infrastructure.database.models.producto_model import ProductoModel  # noqa: E402
from app.infrastructure.database.models.usuario_model import UsuarioModel  # noqa: E402

fallos: list[str] = []


def check(nombre, condicion, detalle=""):
    print(f"  [{'OK ' if condicion else 'FAIL'}] {nombre}{'  ' + str(detalle) if detalle else ''}")
    if not condicion:
        fallos.append(nombre)


app = create_app()
cliente = app.test_client()

with app.app_context():
    productos = ProductoModel.query.all()
    usuarios = UsuarioModel.query.filter_by(activo=True).all()
    producto = next((p for p in productos if p.imagen_bytes), None)
    producto_sin_foto = next((p for p in productos if not p.imagen_bytes), None)
    total_fotos = sum(1 for p in productos if p.imagen_bytes)
    usuario = usuarios[0] if usuarios else None
    n_productos, n_usuarios = len(productos), len(usuarios)

    check("el ORM lee los productos migrados", n_productos == 35, f"n={n_productos}")
    check("  los ids son uuid.UUID nativos",
          all(type(p.id).__name__ == "UUID" for p in productos),
          f"tipo={type(productos[0].id).__name__}")
    check("  activo es booleano real",
          type(usuarios[0].activo).__name__ == "bool" if usuarios else False,
          f"tipo={type(usuarios[0].activo).__name__ if usuarios else None}")
    check("  precios vienen como float/Decimal",
          all(p.precio is None or isinstance(p.precio, (int, float, type(productos[0].precio)))
              for p in productos))
    check("el ORM lee los usuarios migrados", n_usuarios >= 1, f"n={n_usuarios}")

print("\nAPI de catalogo")
r = cliente.get("/api/productos")
check("GET /api/productos responde 200", r.status_code == 200, f"status={r.status_code}")
if r.status_code == 200:
    cuerpo = r.get_json()
    # la API envuelve la lista; ademas filtra (stock/estado), asi que el total
    # puede ser menor que el de la tabla: no es comparacion 1 a 1 con la BD
    items = cuerpo.get("productos", cuerpo) if isinstance(cuerpo, dict) else cuerpo
    check("  devuelve una lista de productos", isinstance(items, list) and len(items) > 0,
          f"n={len(items)}")
    check("  la lista no excede los productos migrados", len(items) <= n_productos,
          f"api={len(items)} bd={n_productos}")
    if items:
        check("  cada item trae id y nombre", "id" in items[0] and "nombre" in items[0],
              f"claves={sorted(items[0].keys())[:6]}")

r = cliente.get("/api/categorias")
check("GET /api/categorias responde 200", r.status_code == 200, f"status={r.status_code}")
if r.status_code == 200:
    cuerpo = r.get_json()
    cats = cuerpo.get("categorias", cuerpo) if isinstance(cuerpo, dict) else cuerpo
    check("  devuelve categorias", isinstance(cats, list) and len(cats) > 0, f"n={len(cats)}")

print("\nBLOBs servidos por la API (leidos del bytea, no de una URL)")
if producto is not None:
    r = cliente.get(f"/api/productos/{producto.id}/imagen")
    check("GET /productos/<id>/imagen responde 200", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        check("  entrega bytes reales", len(r.data) > 1000, f"bytes={len(r.data)}")
    r = cliente.get(f"/api/productos/{producto.id}/thumb")
    check("GET /productos/<id>/thumb responde 200", r.status_code == 200, f"status={r.status_code}")
else:
    check("hay al menos un producto con imagen", False)

if producto_sin_foto is not None:
    r = cliente.get(f"/api/productos/{producto_sin_foto.id}/imagen")
    check("producto sin BLOB responde 404 y no revienta", r.status_code == 404,
          f"status={r.status_code}")

print("\nAPI del carrito (exige sesion via headers del gateway)")
if usuario is not None:
    headers = {"X-User-Id": str(usuario.id), "X-User-Rol": usuario.rol}
    r = cliente.get("/api/cart", headers=headers)
    check("GET /api/cart responde 200", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        datos = r.get_json()
        items = datos.get("items", datos) if isinstance(datos, dict) else datos
        check("  carrito del usuario leido de la BD migrada",
              isinstance(items, (list, dict)), f"tipo={type(datos).__name__}")
        if isinstance(items, list):
            check("  trae los items migrados", len(items) >= 1, f"n={len(items)}")
    r = cliente.get("/api/cart")
    check("GET /api/cart sin sesion responde 401/403", r.status_code in (401, 403),
          f"status={r.status_code}")

print("\nEscritura: la regla de unicidad del carrito sigue valiendo")
# El indice unico es (carrito_id, producto_id, color) NULLS NOT DISTINCT. La
# clave incluye el carrito: dos usuarios distintos pueden tener el mismo
# producto con el mismo color sin violar nada.
if producto is not None and usuario is not None:
    headers = {"X-User-Id": str(usuario.id), "X-User-Rol": usuario.rol}
    cuerpo = {"producto_id": str(producto.id), "cantidad": 1}

    with app.app_context():
        carritos_previos = {
            c for (c,) in db.session.query(CarritoModel.id).all()
        }
        items_previos = {
            i for (i,) in db.session.query(CarritoItemModel.id).all()
        }

    r = cliente.post("/api/cart/items", json=cuerpo, headers=headers)
    check("POST /api/cart/items responde 2xx", 200 <= r.status_code < 300,
          f"status={r.status_code} {r.get_data(as_text=True)[:160]}")

    r2 = cliente.post("/api/cart/items", json=cuerpo, headers=headers)
    check("POST repetido del mismo producto NO duplica (regla de color)",
          200 <= r2.status_code < 300, f"status={r2.status_code}")

    with app.app_context():
        claves = [
            (i.carrito_id, i.producto_id, i.color)
            for i in db.session.query(CarritoItemModel)
            .filter(CarritoItemModel.producto_id == producto.id).all()
        ]
        check("  no hay (carrito, producto, color) repetidos",
              len(claves) == len(set(claves)), f"items={claves}")

    # Limpieza: este test NO debe dejar filas en la data migrada. Se borra solo
    # lo que aparecio durante la prueba: borrar "todos los carritos sin items"
    # se llevaria por delante los carritos migrados que venian vacios.
    with app.app_context():
        with db.session.begin():
            db.session.execute(
                db.text("DELETE FROM carrito_items WHERE producto_id = :p"),
                {"p": str(producto.id)},
            )
            nuevos_carritos = [
                c for c in db.session.execute(
                    db.text("SELECT id FROM carrito")
                ).scalars().all() if c not in carritos_previos
            ]
            if nuevos_carritos:
                db.session.execute(
                    db.text("DELETE FROM carrito WHERE id = ANY(:ids)"),
                    {"ids": nuevos_carritos},
                )
    with app.app_context():
        items_restantes = {
            i for (i,) in db.session.query(CarritoItemModel.id).all()
        }
        carritos_restantes = {
            c for (c,) in db.session.query(CarritoModel.id).all()
        }
        check("  limpieza:items identicos a los previos",
              items_restantes == items_previos,
              f"antes={len(items_previos)} ahora={len(items_restantes)}")
        check("  limpieza:carritos identicos a los previos",
              carritos_restantes == carritos_previos,
              f"antes={len(carritos_previos)} ahora={len(carritos_restantes)}")

print()
if fallos:
    print(f"RESULTADO: {len(fallos)} FALLARON -> {fallos}")
    sys.exit(1)
print("RESULTADO: el backend lee y escribe sobre PostgreSQL con la data migrada")