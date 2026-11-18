

from __future__ import annotations

import uuid

import pytest

from app.infrastructure.database.connection import db
from app.infrastructure.database.models.detalle_pedido_model import (
    DetallePedidoModel,
)
from app.infrastructure.database.models.pedido_model import PedidoModel
from app.infrastructure.database.models.usuario_model import UsuarioModel


def _cabeceras(usuario, rol: str = "cliente") -> dict:
    return {"X-User-Id": str(usuario.id), "X-User-Rol": rol}


def _pedido(usuario, productos, estado: str = "entregado") -> uuid.UUID:
    pedido = PedidoModel(
        usuario_id=usuario.id,
        total=1000 * len(productos),
        entrega="retiro",
        estado=estado,
    )
    for prod in productos:
        pedido.detalles.append(
            DetallePedidoModel(
                producto_id=prod.id, cantidad=1, precio_unitario=1000
            )
        )
    db.session.add(pedido)
    db.session.commit()
    return pedido.id


def _otro_usuario(db_sesion, centinela) -> UsuarioModel:
    u = UsuarioModel(
        email=f"{centinela}-otro@caracterizacion.test",
        password_hash="r0-no-se-usa",
        nombre="R0 Caracterizacion",
        apellido="Otro",
    )
    db_sesion.add(u)
    db_sesion.commit()
    return u


def _admin(db_sesion, centinela) -> UsuarioModel:
    u = UsuarioModel(
        email=f"{centinela}-admin@caracterizacion.test",
        password_hash="r0-no-se-usa",
        nombre="R0 Caracterizacion",
        apellido="Admin",
        rol="admin",
    )
    db_sesion.add(u)
    db_sesion.commit()
    return u


def _resenas_en_la_base(pedido_id) -> int:
    return db.session.execute(
        db.text("SELECT count(*) FROM resenas WHERE pedido_id = :p"),
        {"p": pedido_id},
    ).scalar_one()


def _url_resenas(pedido_id) -> str:
    return f"/api/pedidos/{pedido_id}/resenas"


def _url_resenas_producto(producto_id) -> str:
    return f"/api/productos/{producto_id}/resenas"


def _publico_producto(client, prod) -> dict:
    respuesta = client.get("/api/productos")
    assert respuesta.status_code == 200, respuesta.get_json()
    return next(
        p for p in respuesta.get_json()["productos"] if p["id"] == str(prod.id)
    )


def _pedido_en_el_listado(client, usuario, pedido_id) -> dict:
    respuesta = client.get("/api/pedidos", headers=_cabeceras(usuario))
    assert respuesta.status_code == 200, respuesta.get_json()
    return next(
        p
        for p in respuesta.get_json()["pedidos"]
        if p["id"] == str(pedido_id)
    )




def test_post_feliz_responde_201_y_persiste(client, usuario, producto):
    prod = producto()
    pedido_id = _pedido(usuario, [prod])

    respuesta = client.post(
        _url_resenas(pedido_id),
        json={"producto_id": str(prod.id), "estrellas": 4},
        headers=_cabeceras(usuario),
    )

    assert respuesta.status_code == 201, respuesta.get_json()
    cuerpo = respuesta.get_json()
    assert cuerpo["producto_id"] == str(prod.id)
    assert cuerpo["estrellas"] == 4
    assert _resenas_en_la_base(pedido_id) == 1, (
        "la API respondió 201 pero la reseña no quedó en la base"
    )


def test_pedido_no_entregado_es_409(client, usuario, producto):
    prod = producto()
    pedido_id = _pedido(usuario, [prod], estado="pendiente")

    respuesta = client.post(
        _url_resenas(pedido_id),
        json={"producto_id": str(prod.id), "estrellas": 5},
        headers=_cabeceras(usuario),
    )

    assert respuesta.status_code == 409, respuesta.get_json()
    assert respuesta.get_json()["mensaje"], "el frontend muestra err.message"
    assert _resenas_en_la_base(pedido_id) == 0


def test_duplicado_es_409_y_la_original_queda_intacta(client, usuario, producto):
    prod = producto()
    pedido_id = _pedido(usuario, [prod])
    url = _url_resenas(pedido_id)
    headers = _cabeceras(usuario)
    client.post(
        url, json={"producto_id": str(prod.id), "estrellas": 4}, headers=headers
    )

    respuesta = client.post(
        url, json={"producto_id": str(prod.id), "estrellas": 2}, headers=headers
    )

    assert respuesta.status_code == 409, respuesta.get_json()
    assert _resenas_en_la_base(pedido_id) == 1
    estrellas = db.session.execute(
        db.text("SELECT estrellas FROM resenas WHERE pedido_id = :p"),
        {"p": pedido_id},
    ).scalar_one()
    assert int(estrellas) == 4, (
        "el POST duplicado con otras estrellas piso la original: es inmutable"
    )


def test_no_dueno_del_pedido_es_403(client, usuario, producto, db_sesion, centinela):
    prod = producto()
    pedido_id = _pedido(usuario, [prod])
    otro = _otro_usuario(db_sesion, centinela)

    respuesta = client.post(
        _url_resenas(pedido_id),
        json={"producto_id": str(prod.id), "estrellas": 5},
        headers=_cabeceras(otro),
    )

    assert respuesta.status_code == 403, respuesta.get_json()
    assert _resenas_en_la_base(pedido_id) == 0


def test_producto_fuera_del_pedido_es_404(client, usuario, producto, centinela):
    incluido = producto()
    ajeno = producto(nombre=f"{centinela}-ajeno")
    pedido_id = _pedido(usuario, [incluido])

    respuesta = client.post(
        _url_resenas(pedido_id),
        json={"producto_id": str(ajeno.id), "estrellas": 5},
        headers=_cabeceras(usuario),
    )

    assert respuesta.status_code == 404, respuesta.get_json()
    assert _resenas_en_la_base(pedido_id) == 0


@pytest.mark.parametrize("estrellas", [0, 6, 3.5, "x"])
def test_estrellas_fuera_de_1_a_5_o_no_enteras_es_400(
    client, usuario, producto, estrellas
):
    prod = producto()
    pedido_id = _pedido(usuario, [prod])

    respuesta = client.post(
        _url_resenas(pedido_id),
        json={"producto_id": str(prod.id), "estrellas": estrellas},
        headers=_cabeceras(usuario),
    )

    assert respuesta.status_code == 400, respuesta.get_json()
    assert _resenas_en_la_base(pedido_id) == 0




def test_get_devuelve_las_resenas_del_pedido_para_precarga(client, usuario, producto):
    p1 = producto()
    p2 = producto(nombre=f"{p1.nombre}-b")
    pedido_id = _pedido(usuario, [p1, p2])
    url = _url_resenas(pedido_id)
    headers = _cabeceras(usuario)
    client.post(url, json={"producto_id": str(p1.id), "estrellas": 4}, headers=headers)
    client.post(url, json={"producto_id": str(p2.id), "estrellas": 5}, headers=headers)

    respuesta = client.get(url, headers=headers)

    assert respuesta.status_code == 200, respuesta.get_json()
    resenas = respuesta.get_json()["resenas"]
    por_producto = {r["producto_id"]: r["estrellas"] for r in resenas}
    assert por_producto == {str(p1.id): 4, str(p2.id): 5}, (
        "la precarga del modal debe devolver exactamente lo ya reseñado"
    )


def test_get_de_otro_usuario_es_403(client, usuario, producto, db_sesion, centinela):
    prod = producto()
    pedido_id = _pedido(usuario, [prod])
    otro = _otro_usuario(db_sesion, centinela)

    respuesta = client.get(_url_resenas(pedido_id), headers=_cabeceras(otro))

    assert respuesta.status_code == 403, respuesta.get_json()


def test_get_de_pedido_inexistente_es_404(client, usuario):
    respuesta = client.get(
        _url_resenas(uuid.uuid4()), headers=_cabeceras(usuario)
    )

    assert respuesta.status_code == 404, respuesta.get_json()


def test_get_el_admin_tambien_puede_ver(client, usuario, producto, db_sesion, centinela):
    prod = producto()
    pedido_id = _pedido(usuario, [prod])
    admin = _admin(db_sesion, centinela)
    client.post(
        _url_resenas(pedido_id),
        json={"producto_id": str(prod.id), "estrellas": 5},
        headers=_cabeceras(usuario),
    )

    respuesta = client.get(_url_resenas(pedido_id), headers=_cabeceras(admin, "admin"))

    assert respuesta.status_code == 200, respuesta.get_json()
    assert len(respuesta.get_json()["resenas"]) == 1




def test_resenas_pendientes_es_1_en_entregado_con_productos_sin_resenar(
    client, usuario, producto
):
    p1 = producto()
    p2 = producto(nombre=f"{p1.nombre}-b")
    pedido_id = _pedido(usuario, [p1, p2])

    nuestro = _pedido_en_el_listado(client, usuario, pedido_id)

    assert nuestro["resenas_pendientes"] == 1, (
        "un pedido entregado con productos sin reseñar debe mostrar el badge 1"
    )


def test_resenas_pendientes_pasa_a_0_cuando_todo_esta_resenado(
    client, usuario, producto
):
    p1 = producto()
    p2 = producto(nombre=f"{p1.nombre}-b")
    pedido_id = _pedido(usuario, [p1, p2])
    url = _url_resenas(pedido_id)
    headers = _cabeceras(usuario)
    client.post(url, json={"producto_id": str(p1.id), "estrellas": 4}, headers=headers)
    respuesta = client.post(
        url, json={"producto_id": str(p2.id), "estrellas": 5}, headers=headers
    )
    assert respuesta.status_code == 201, respuesta.get_json()

    nuestro = _pedido_en_el_listado(client, usuario, pedido_id)

    assert nuestro["resenas_pendientes"] == 0, (
        "con todos los productos reseñados el badge debe bajar a 0"
    )


def test_resenas_pendientes_es_0_si_el_pedido_no_esta_entregado(
    client, usuario, producto
):
    pedido_id = _pedido(usuario, [producto()], estado="pendiente")

    nuestro = _pedido_en_el_listado(client, usuario, pedido_id)

    assert nuestro["resenas_pendientes"] == 0




def test_catalogo_sin_resenas_expone_rating_null_y_contador_cero(client, producto):
    prod = producto()

    publico = _publico_producto(client, prod)

    assert publico["rating"] is None, (
        "un producto sin reseñas debe exponer rating null, no 0"
    )
    assert publico["resenas_count"] == 0


def test_catalogo_expone_promedio_un_decimal_y_contador(
    client, usuario, producto, db_sesion, centinela
):
    prod = producto()
    otro = _otro_usuario(db_sesion, centinela)
    pedido_mio = _pedido(usuario, [prod])
    pedido_otro = _pedido(otro, [prod])
    client.post(
        _url_resenas(pedido_mio),
        json={"producto_id": str(prod.id), "estrellas": 4},
        headers=_cabeceras(usuario),
    )
    respuesta = client.post(
        _url_resenas(pedido_otro),
        json={"producto_id": str(prod.id), "estrellas": 5},
        headers=_cabeceras(otro),
    )
    assert respuesta.status_code == 201, respuesta.get_json()

    publico = _publico_producto(client, prod)

    assert publico["rating"] == 4.5
    assert publico["resenas_count"] == 2
    assert "usuario_id" not in publico, (
        "la superficie pública nunca expone quién reseñó"
    )




def test_post_con_comentario_lo_recorta_y_persiste(client, usuario, producto):
    prod = producto()
    pedido_id = _pedido(usuario, [prod])

    respuesta = client.post(
        _url_resenas(pedido_id),
        json={
            "producto_id": str(prod.id),
            "estrellas": 4,
            "comentario": "  Muy bueno  ",
        },
        headers=_cabeceras(usuario),
    )

    assert respuesta.status_code == 201, respuesta.get_json()
    assert respuesta.get_json()["comentario"] == "Muy bueno"
    comentario = db.session.execute(
        db.text("SELECT comentario FROM resenas WHERE pedido_id = :p"),
        {"p": pedido_id},
    ).scalar_one()
    assert comentario == "Muy bueno", (
        "la API respondió 201 pero el comentario no quedó en la base"
    )


def test_get_publico_por_producto_sin_sesion(client, usuario, producto):
    prod = producto()
    pedido_id = _pedido(usuario, [prod])
    client.post(
        _url_resenas(pedido_id),
        json={
            "producto_id": str(prod.id),
            "estrellas": 4,
            "comentario": "Bueno",
        },
        headers=_cabeceras(usuario),
    )

    respuesta = client.get(_url_resenas_producto(prod.id))

    assert respuesta.status_code == 200, respuesta.get_json()
    resenas = respuesta.get_json()["resenas"]
    assert len(resenas) == 1
    publica = resenas[0]
    assert publica["estrellas"] == 4
    assert publica["comentario"] == "Bueno"
    assert publica["autor"], "la vista pública debe exponer el nombre del autor"
    assert "usuario_id" not in publica, (
        "la superficie pública nunca expone quién reseñó"
    )


def test_get_publico_por_producto_inexistente_es_404(client):
    respuesta = client.get(_url_resenas_producto(uuid.uuid4()))

    assert respuesta.status_code == 404, respuesta.get_json()
