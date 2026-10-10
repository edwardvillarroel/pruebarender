"""La linea del carrito tiene que traer la foto que le corresponde.

El carrito, el navbar y el checkout renderizan `{item.imagen && <img .../>}`.
El backend mandaba `producto_id` y el NOMBRE del color, pero no la foto, asi
que el frontend trataba de resolverla con un `Map` en memoria que solo se
llenaba al abrir la ficha del producto (`services/products.js`). Al recargar o
entrar directo a /carrito o /checkout ese Map estaba vacio y la linea caia al
fallback: la foto PRINCIPAL del producto, que para un producto con variantes
es justo la que el usuario no eligio (o nada, si el catalogo no habia cargado).

Ahora la resuelve el repositorio contra la base y viaja en el JSON. La regla es
la misma que usa la ficha (`ProductoDetalle.jsx`): foto del color elegido si el
color tiene foto propia, y si no la del producto.
"""

from __future__ import annotations

import uuid

from app.infrastructure.database.models.producto_color_model import ProductoColorModel


def _cabeceras(usuario) -> dict:
    return {"X-User-Id": str(usuario.id), "X-User-Rol": "cliente"}


def _agregar_color(db_sesion, producto_id, nombre: str, con_foto: bool = True):
    """Inserta un color del producto, con o sin BLOB de foto."""
    color = ProductoColorModel(
        id=uuid.uuid4(),
        producto_id=producto_id,
        nombre=nombre,
        orden=0,
    )
    if con_foto:
        color.imagen_bytes = b"f" * 4000
        color.imagen_content_type = "image/jpeg"
    db_sesion.add(color)
    db_sesion.commit()
    return color


def test_linea_con_color_trae_la_foto_del_color(client, producto, usuario, db_sesion):
    """El caso del bug: color elegido -> foto de ESE color, no la principal."""
    p = producto(stock=10)
    p.imagen_bytes = b"p" * 4000
    p.imagen_content_type = "image/jpeg"
    db_sesion.commit()
    color = _agregar_color(db_sesion, p.id, "Rojo")

    respuesta = client.post(
        "/api/cart/items",
        json={"producto_id": str(p.id), "cantidad": 1, "color": "Rojo"},
        headers=_cabeceras(usuario),
    )
    assert respuesta.status_code == 201, respuesta.get_json()

    # El POST devuelve el carrito entero: tiene que traer la MISMA foto que el
    # GET. Si solo se resolviera al leer, el mismo campo volveria con imagen en
    # una respuesta y sin imagen en la otra.
    item = respuesta.get_json()["carrito"]["items"][0]
    assert item["imagen"] == f"/api/productos/colores/{color.id}/imagen", (
        f"el POST no resolvio la foto del color: {item['imagen']!r}"
    )


def test_linea_con_color_trae_la_foto_del_color_al_recargar(
    client, producto, usuario, db_sesion
):
    """El GET es el camino de recarga: entrar directo a /carrito sin la ficha.

    Es el escenario que fallaba: el Map del frontend arranca vacio en una
    pestana nueva, asi que si la foto no viene del backend no hay de donde
    sacarla.
    """
    p = producto(stock=10)
    p.imagen_bytes = b"p" * 4000
    db_sesion.commit()
    color = _agregar_color(db_sesion, p.id, "Negro")

    cabeceras = _cabeceras(usuario)
    assert (
        client.post(
            "/api/cart/items",
            json={"producto_id": str(p.id), "cantidad": 1, "color": "Negro"},
            headers=cabeceras,
        ).status_code
        == 201
    )

    respuesta = client.get("/api/cart", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.get_json()

    item = respuesta.get_json()["carrito"]["items"][0]
    assert item["imagen"] == f"/api/productos/colores/{color.id}/imagen"


def test_linea_sin_color_trae_la_foto_del_producto(client, producto, usuario, db_sesion):
    """Sin variante elegida, la foto es la principal del producto."""
    p = producto(stock=10)
    p.imagen_bytes = b"p" * 4000
    db_sesion.commit()

    respuesta = client.post(
        "/api/cart/items",
        json={"producto_id": str(p.id), "cantidad": 1},
        headers=_cabeceras(usuario),
    )
    assert respuesta.status_code == 201, respuesta.get_json()

    item = respuesta.get_json()["carrito"]["items"][0]
    assert item["imagen"] == f"/api/productos/{p.id}/imagen"


def test_color_sin_foto_propia_cae_a_la_del_producto(
    client, producto, usuario, db_sesion
):
    """Un color cargado sin foto no puede dejar la linea sin imagen.

    El admin puede crear el color antes de subirle la foto (o la subida
    fallo), asi que el color sin BLOB no puede ganarle a la foto valida del
    producto.
    """
    p = producto(stock=10)
    p.imagen_bytes = b"p" * 4000
    db_sesion.commit()
    _agregar_color(db_sesion, p.id, "Azul", con_foto=False)

    respuesta = client.post(
        "/api/cart/items",
        json={"producto_id": str(p.id), "cantidad": 1, "color": "Azul"},
        headers=_cabeceras(usuario),
    )
    assert respuesta.status_code == 201, respuesta.get_json()

    item = respuesta.get_json()["carrito"]["items"][0]
    assert item["imagen"] == f"/api/productos/{p.id}/imagen", (
        f"un color sin foto no debe dejar la linea sin imagen: {item['imagen']!r}"
    )


def test_color_sin_matchear_cae_a_la_del_producto(client, producto, usuario, db_sesion):
    """Si el nombre del color no existe en la base, no se rompe: fallback.

    `carrito_items.color` guarda el nombre como texto libre, asi que puede
    quedar un color que despues se renombro o se borro. La linea tiene que
    seguir mostrando algo.
    """
    p = producto(stock=10)
    p.imagen_bytes = b"p" * 4000
    db_sesion.commit()

    respuesta = client.post(
        "/api/cart/items",
        json={"producto_id": str(p.id), "cantidad": 1, "color": "ColorQueNoExiste"},
        headers=_cabeceras(usuario),
    )
    assert respuesta.status_code == 201, respuesta.get_json()

    item = respuesta.get_json()["carrito"]["items"][0]
    assert item["imagen"] == f"/api/productos/{p.id}/imagen"


def test_producto_y_color_sin_foto_dan_null(client, producto, usuario, db_sesion):
    """Sin ninguna foto disponible, `imagen` es `null` y el frontend no rompe.

    `null` y no cadena vacia, para que `{item.imagen && ...}` sea falso y no
    intente montar un `<img src="">`.
    """
    p = producto(stock=10)
    db_sesion.commit()

    respuesta = client.post(
        "/api/cart/items",
        json={"producto_id": str(p.id), "cantidad": 1},
        headers=_cabeceras(usuario),
    )
    assert respuesta.status_code == 201, respuesta.get_json()

    item = respuesta.get_json()["carrito"]["items"][0]
    assert item["imagen"] is None