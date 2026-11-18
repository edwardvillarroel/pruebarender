




from __future__ import annotations

from decimal import Decimal


def _producto_por_id(productos_json, producto_id) -> dict | None:
    for datos in productos_json:
        if datos["id"] == str(producto_id):
            return datos
    return None


def test_montos_de_producto_viajan_como_numero(
    client, producto, db_sesion, centinela
):
    p = producto(stock=5, precio=Decimal("7140.50"))
    p.descuento = Decimal("140.25")
    p.precio_original = Decimal("7280.75")
    db_sesion.commit()
    producto_id = p.id
    db_sesion.expunge_all()

    respuesta = client.get("/api/productos")
    assert respuesta.status_code == 200, respuesta.get_json()

    datos = _producto_por_id(respuesta.get_json()["productos"], producto_id)
    assert datos is not None, f"el producto {centinela} no vino en /api/productos"

    assert not isinstance(datos["precio"], str), (
        f"precio volvio como string ({datos['precio']!r}): el frontend no le puede "
        f"aplicar toLocaleString('es-CL')"
    )
    assert isinstance(datos["precio"], (int, float)), (
        f"precio no es numero JSON: {type(datos['precio'])}"
    )
    assert datos["precio"] == 7140.5

    assert not isinstance(datos["descuento"], str), (
        f"descuento volvio como string ({datos['descuento']!r})"
    )
    assert isinstance(datos["descuento"], (int, float))
    assert datos["descuento"] == 140.25

    assert not isinstance(datos["precio_original"], str), (
        f"precio_original volvio como string ({datos['precio_original']!r})"
    )
    assert datos["precio_original"] == 7280.75


def test_montos_redondeados_y_nulos(client, producto, db_sesion, centinela):

    p = producto(stock=5, precio=Decimal("5000.00"))
    db_sesion.commit()
    producto_id = p.id
    db_sesion.expunge_all()

    respuesta = client.get("/api/productos")
    assert respuesta.status_code == 200, respuesta.get_json()

    datos = _producto_por_id(respuesta.get_json()["productos"], producto_id)
    assert datos is not None, f"el producto {centinela} no vino en /api/productos"

    assert datos["precio"] == 5000
    assert isinstance(datos["precio"], int), (
        f"un peso entero deberia salir como int, no {type(datos['precio'])}"
    )
    assert datos["descuento"] is None
    assert datos["precio_original"] is None


def test_stock_producto_viaja_como_numero(client, producto, db_sesion, centinela):

    producto(stock=10)
    db_sesion.commit()
    db_sesion.expunge_all()

    respuesta = client.get("/api/productos")
    assert respuesta.status_code == 200, respuesta.get_json()

    assert respuesta.get_json()["productos"], "no vinieron productos"
    for datos in respuesta.get_json()["productos"]:
        assert not isinstance(datos["stock"], str), (
            f"stock volvio como string ({datos['stock']!r})"
        )
        assert isinstance(datos["stock"], (int, float))


def test_cantidad_de_carrito_viaja_como_numero(client, producto, usuario):

    p = producto(stock=10)
    cabeceras = {"X-User-Id": str(usuario.id), "X-User-Rol": "cliente"}

    for color in ("rojo", "negro"):
        respuesta = client.post(
            "/api/cart/items",
            json={"producto_id": str(p.id), "cantidad": 1, "color": color},
            headers=cabeceras,
        )
        assert respuesta.status_code == 201, respuesta.get_json()

    respuesta = client.get("/api/cart", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.get_json()

    items = respuesta.get_json()["carrito"]["items"]
    assert len(items) == 2, f"se esperaban 2 lineas, llegaron {len(items)}"

    for item in items:
        assert not isinstance(item["cantidad"], str), (
            f"cantidad volvio como string ({item['cantidad']!r}): con `+` el "
            f"frontend concatena en vez de sumar"
        )
        assert isinstance(item["cantidad"], (int, float))

    total = 0
    for item in items:
        total = total + item["cantidad"]

    assert total == 2, (
        f"el badge aria {total!r} en vez de 2: con `cantidad` como string el "
        f"`+` de `reduce` concatena"
    )
    assert isinstance(total, int)