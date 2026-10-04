"""Toda columna `numeric` de Postgres tiene que viajar como NUMERO JSON.

Postgres devuelve `Decimal` para las columnas `numeric(...)` y el mapper
ORM -> dominio no castea (la anotacion `int` de la entidad es una declaracion,
no una coercion), asi que el `Decimal` llega intacto a `jsonify`. Flask lo
serializa como string: `{"precio": "7140.50"}`.

En el frontend eso rompe el formato sin avisar, porque los strings no tienen
`toLocaleString`: `"7140.50".toLocaleString('es-CL')` ignora el locale y JS cae
al de `Object.prototype`, devolviendo el texto crudo. Lo confuso es que el
subtotal SI se ve bien, porque `item.precio * item.cantidad` si coerciona a
numero en la aritmetica. Un precio unitario con `$7140.50` al lado de un
subtotal con `$14.281` en la misma linea.

Con `+` es PEOR, porque concatena en vez de sumar. El badge del carrito hacia
`items.reduce((acc, i) => acc + i.cantidad, 0)`: con `cantidad` como string,
`0 + "1"` daba `"01"`, y al segundo item `"011"`. El badge de un carrito con
dos productos de cantidad 1 mostraba `011` en vez de `2`.

Estos tests fijan el contrato. El mecanismo es un proveedor JSON global en
`app/api/json_provider.py`: castear campo por campo en cada serializer se
demostro que fuga (se escaparon `stock`, `rating` y `cantidad`), asi que hay
un solo mecanismo y no se puede olvidar el proximo campo.
"""

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
    """Con centavos en la base, el JSON tiene que traer numeros."""
    p = producto(stock=5, precio=Decimal("7140.50"))
    p.descuento = Decimal("140.25")
    p.precio_original = Decimal("7280.75")
    db_sesion.commit()
    producto_id = p.id
    # Se saca del identity map a proposito: si el objeto quedara en memoria, el
    # `Decimal` vendria del INSERT de Python y el test no probaria el
    # `numeric(10,2)` de verdad. Expulsado, la API lo vuelve a LEER de la base
    # y reproduce el bug de punta a punta.
    db_sesion.expunge_all()

    respuesta = client.get("/api/productos")
    assert respuesta.status_code == 200, respuesta.get_json()

    datos = _producto_por_id(respuesta.get_json()["productos"], producto_id)
    assert datos is not None, f"el producto {centinela} no vino en /api/productos"

    # El tipo ES el contrato: un string obliga a que cada consumidor se acuerde
    # de castear, y ese es el bug.
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
    """Pesos enteros salen como `int`; un `NULL` sigue siendo `null`, no `0`.

    El `None` importa: `descuento` y `precio_original` son nullable, y `0` no
    es lo mismo que "sin descuento", porque la card muestra el precio tachado
    solo si hay descuento real.
    """
    p = producto(stock=5, precio=Decimal("5000.00"))
    db_sesion.commit()
    producto_id = p.id
    db_sesion.expunge_all()

    respuesta = client.get("/api/productos")
    assert respuesta.status_code == 200, respuesta.get_json()

    datos = _producto_por_id(respuesta.get_json()["productos"], producto_id)
    assert datos is not None, f"el producto {centinela} no vino en /api/productos"

    # Pesos enteros: `int`, no `5000.0`, para no ensuciar el payload.
    assert datos["precio"] == 5000
    assert isinstance(datos["precio"], int), (
        f"un peso entero deberia salir como int, no {type(datos['precio'])}"
    )
    assert datos["descuento"] is None
    assert datos["precio_original"] is None


def test_stock_producto_viaja_como_numero(client, producto, db_sesion, centinela):
    """`productos.stock` tambien es `numeric` y debe salir como numero.

    Este campo se habia escapado del fix por campo: `Inventario.jsx` renderiza
    `{p.stock}` directo, asi que un string se veria tal cual en pantalla.
    """
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
    """Regresion del badge `011`: `cantidad` tiene que ser numero.

    Arma DOS lineas de cantidad 1 (mismo producto, distinto color) porque
    una sola linea de cantidad 2 no reproduce el bug: con un unico item el
    `reduce` arranque en `0` y `0 + "2"` no concatena. Necesitan ser dos
    strings distintos para que `0 + "1"` + `"1"` de `"011"`.
    """
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

    # La aritmetica exacta del badge (`CartContext.jsx`):
    #   items.reduce((acc, i) => acc + i.cantidad, 0)
    total = 0
    for item in items:
        total = total + item["cantidad"]

    assert total == 2, (
        f"el badge aria {total!r} en vez de 2: con `cantidad` como string el "
        f"`+` de `reduce` concatena"
    )
    assert isinstance(total, int)