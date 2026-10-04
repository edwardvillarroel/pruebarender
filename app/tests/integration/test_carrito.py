"""Caracterizacion del carrito: agrupacion por producto Y color.

El caso que mas riesgo tiene en la migracion es el `color` NULL. En Oracle un
indice unico NO considera NULL igual a NULL, asi que el mismo producto sin
color podia repetirse en el carrito. En PostgreSQL hace falta `NULLS NOT
DISTINCT` para reproducirlo. Estos tests fijan que hay exactamente UNA linea
por (producto, color) con color NULL, que es lo que espera el negocio.
"""

from __future__ import annotations

import pytest

from app.application.carrito.gestionar_carrito import GestionarCarrito, ItemCarritoNoEncontrado
from app.infrastructure.repositories.carrito_repository_bd import CarritoRepositoryBd
from app.infrastructure.database.connection import db


@pytest.fixture
def carrito(db_sesion, usuario):
    return GestionarCarrito(CarritoRepositoryBd())


def test_carreto_inexistente_se_crea_al_pedirlo(carrito, usuario, db_sesion):
    import uuid as _uuid

    c = carrito.obtener(str(usuario.id))
    assert c is not None
    assert c.items == []
    assert c.usuario_id == str(usuario.id)

    # La entidad de dominio no expone `id` (solo el modelo ORM), asi que el
    # invariante real se verifica contra la base: pedirlo dos veces no puede
    # crear un segundo carrito para el mismo usuario.
    carrito.obtener(str(usuario.id))
    filas = db_sesion.execute(
        db.text("SELECT count(*) FROM carrito WHERE usuario_id = :u"),
        {"u": _uuid.UUID(str(usuario.id))},
    ).scalar_one()
    assert filas == 1, f"se esperaban 1 carrito en la base, hubo {filas}"


def test_mismo_producto_sin_color_agrupa_en_una_sola_linea(
    carrito, usuario, producto
):
    p = producto(stock=50)
    uid = str(usuario.id)

    carrito.agregar_item(uid, str(p.id), 2)
    carrito.agregar_item(uid, str(p.id), 3)

    items = carrito.obtener(uid).items
    assert len(items) == 1, f"se esperaba 1 linea sin color, hubo {len(items)}"
    assert items[0].cantidad == 5
    assert items[0].color is None


def test_mismo_producto_con_color_agrupa(carrito, usuario, producto):
    p = producto(stock=50)
    uid = str(usuario.id)

    carrito.agregar_item(uid, str(p.id), 2, "rojo")
    carrito.agregar_item(uid, str(p.id), 3, "rojo")

    items = carrito.obtener(uid).items
    assert len(items) == 1
    assert items[0].cantidad == 5
    assert items[0].color == "rojo"


def test_mismo_producto_colores_distintos_son_lineas_distintas(
    carrito, usuario, producto
):
    p = producto(stock=50)
    uid = str(usuario.id)

    carrito.agregar_item(uid, str(p.id), 1, "rojo")
    carrito.agregar_item(uid, str(p.id), 1, "negro")
    carrito.agregar_item(uid, str(p.id), 1)

    items = carrito.obtener(uid).items
    assert len(items) == 3
    assert sorted(i.color or "" for i in items) == ["", "negro", "rojo"]


def test_color_vacio_o_espacios_normaliza_a_sin_color(carrito, usuario, producto):
    p = producto(stock=50)
    uid = str(usuario.id)

    carrito.agregar_item(uid, str(p.id), 1, "rojo")
    carrito.agregar_item(uid, str(p.id), 1, "")
    carrito.agregar_item(uid, str(p.id), 1, "   ")

    items = carrito.obtener(uid).items
    assert len(items) == 2, "vacio y espacios deben serde la linea sin color"
    colores = sorted(i.color or "" for i in items)
    assert colores == ["", "rojo"]


def test_no_hay_dos_lineas_null_en_la_base(carrito, usuario, producto, db_sesion):
    """Guarda dura: la BD no puede tener dos items del mismo producto con color NULL.

    although la capa de aplicacion ya agrupa, esto verifica el indice unico de
    la base, que es justamente donde Oracle y PostgreSQL se diferencian. En
    Oracle un indice comun NO considera NULL igual a NULL; en PostgreSQL hace
    falta `NULLS NOT DISTINCT` para reproducir la misma regla. Si ese indice
    pierde el `NULLS NOT DISTINCT`, el INSERT de abajo entra y el carrito queda
    con dos lineas del mismo producto sin color.
    """
    import uuid as _uuid
    from sqlalchemy.exc import IntegrityError

    p = producto(stock=50)
    uid = str(usuario.id)

    carrito.agregar_item(uid, str(p.id), 1)

    carrito_id = db_sesion.execute(
        db.text("SELECT id FROM carrito WHERE usuario_id = :u"), {"u": _uuid.UUID(uid)}
    ).scalar_one()

    with pytest.raises(IntegrityError):
        db_sesion.execute(
            db.text(
                "INSERT INTO carrito_items (id, carrito_id, producto_id, cantidad, color, agregado_en) "
                "VALUES (:i, :c, :p, 1, NULL, now())"
            ),
            {"i": _uuid.uuid4(), "c": carrito_id, "p": p.id},
        )
        db_sesion.commit()
    db_sesion.rollback()

    total = db_sesion.execute(
        db.text(
            "SELECT count(*) FROM carrito_items "
            "WHERE producto_id = :p AND color IS NULL"
        ),
        {"p": p.id},
    ).scalar_one()
    assert total == 1, (
        "la base permitio dos lineas con color NULL: el indice unico no trata "
        "los NULL como iguales (falta NULLS NOT DISTINCT)"
    )


def test_actualizar_cantidad_y_eliminar(carrito, usuario, producto):
    p = producto(stock=50)
    uid = str(usuario.id)
    carrito.agregar_item(uid, str(p.id), 2, "rojo")

    item = carrito.obtener(uid).items[0]
    carrito.actualizar_cantidad(uid, item.id, 7)
    assert carrito.obtener(uid).items[0].cantidad == 7

    carrito.eliminar_item(uid, item.id)
    assert carrito.obtener(uid).items == []


def test_item_inexistente_al_actualizar_o_eliminar_falla(carrito, usuario):
    import uuid as _uuid

    uid = str(usuario.id)
    carrito.obtener(uid)
    fantasma = _uuid.uuid4()
    with pytest.raises(ItemCarritoNoEncontrado):
        carrito.actualizar_cantidad(uid, fantasma, 3)
    with pytest.raises(ItemCarritoNoEncontrado):
        carrito.eliminar_item(uid, fantasma)


@pytest.mark.parametrize("cantidad", [0, -1])
def test_cantidad_no_positiva_se_rechaza(carrito, usuario, producto, cantidad):
    p = producto(stock=50)
    with pytest.raises(ValueError):
        carrito.agregar_item(str(usuario.id), str(p.id), cantidad)


def test_vaciar_deja_el_carrito_sin_items(carrito, usuario, producto):
    p = producto(stock=50)
    uid = str(usuario.id)
    carrito.agregar_item(uid, str(p.id), 1, "rojo")
    carrito.agregar_item(uid, str(p.id), 1, "negro")

    carrito.vaciar(uid)
    assert carrito.obtener(uid).items == []


def test_carrito_esta_aislado_por_usuario(carrito, usuario, producto, db_sesion, centinela):
    from app.infrastructure.database.models.usuario_model import UsuarioModel

    # El email debe llevar el prefijo r0- para que la limpieza automatica lo
    # encuentre; si no, el test deja basura y falla el chequeo de residuos.
    otro = UsuarioModel(
        email=f"{centinela}-otro@caracterizacion.test",
        password_hash="r0",
        nombre="Otro",
        apellido="Usuario",
    )
    db_sesion.add(otro)
    db_sesion.commit()

    p = producto(stock=50)
    carrito.agregar_item(str(usuario.id), str(p.id), 1)
    assert len(carrito.obtener(str(usuario.id)).items) == 1
    assert carrito.obtener(str(otro.id)).items == []