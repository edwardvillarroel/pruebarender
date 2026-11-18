


from __future__ import annotations

import uuid

from app.infrastructure.database.models.producto_color_model import ProductoColorModel


def _cabeceras(usuario) -> dict:
    return {"X-User-Id": str(usuario.id), "X-User-Rol": "cliente"}


def _agregar_color(db_sesion, producto_id, nombre: str, con_foto: bool = True):
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

    item = respuesta.get_json()["carrito"]["items"][0]
    assert item["imagen"] == f"/api/productos/colores/{color.id}/thumb", (
        f"el POST no resolvio la foto del color: {item['imagen']!r}"
    )


def test_linea_con_color_trae_la_foto_del_color_al_recargar(
    client, producto, usuario, db_sesion
):

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
    assert item["imagen"] == f"/api/productos/colores/{color.id}/thumb"


def test_linea_sin_color_trae_la_foto_del_producto(client, producto, usuario, db_sesion):
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
    assert item["imagen"] == f"/api/productos/{p.id}/thumb"


def test_color_sin_foto_propia_cae_a_la_del_producto(
    client, producto, usuario, db_sesion
):

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
    assert item["imagen"] == f"/api/productos/{p.id}/thumb", (
        f"un color sin foto no debe dejar la linea sin imagen: {item['imagen']!r}"
    )


def test_color_sin_matchear_cae_a_la_del_producto(client, producto, usuario, db_sesion):

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
    assert item["imagen"] == f"/api/productos/{p.id}/thumb"


def test_producto_y_color_sin_foto_dan_null(client, producto, usuario, db_sesion):

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