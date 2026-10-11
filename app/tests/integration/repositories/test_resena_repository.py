"""Integración del repositorio de reseñas contra `postgres_test`.

El repositorio es el dueño del `UNIQUE (usuario_id, pedido_id, producto_id)`
y del recálculo denormalizado de `productos.rating`/`resenas_count` dentro de
la MISMA transacción del INSERT. Estos tests fijan esos dos invariantes contra
la base real: el índice existe y la violación se traduce a
`ResenaDuplicadaError` (sin dejar la sesión rota), y el promedio con 1 decimal
queda persistido en `productos`, no solo calculado en memoria.
"""

from __future__ import annotations

from uuid import UUID

import pytest

from app.domain.entities.resena import Resena
from app.domain.interfaces.repositories import ResenaDuplicadaError
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.detalle_pedido_model import (
    DetallePedidoModel,
)
from app.infrastructure.database.models.pedido_model import PedidoModel
from app.infrastructure.repositories.resena_repository import ResenaRepository


@pytest.fixture
def repo():
    return ResenaRepository()


def _pedido_con_producto(usuario, prod, estado: str = "entregado") -> UUID:
    """Pedido real con el producto en sus detalles: la FK de `resenas.pedido_id`
    exige la fila, y los tests siguientes cuelgan reseñas de acá."""
    pedido = PedidoModel(
        usuario_id=usuario.id,
        total=5000,
        entrega="retiro",
        estado=estado,
    )
    pedido.detalles.append(
        DetallePedidoModel(producto_id=prod.id, cantidad=1, precio_unitario=5000)
    )
    db.session.add(pedido)
    db.session.commit()
    return pedido.id


def _resena(usuario_id, pedido_id, producto_id, estrellas: int) -> Resena:
    return Resena(
        usuario_id=UUID(str(usuario_id)),
        pedido_id=UUID(str(pedido_id)),
        producto_id=UUID(str(producto_id)),
        estrellas=estrellas,
    )


def _stats_producto(producto_id) -> tuple[float | None, int]:
    """`rating` y `resenas_count` leídos con SQL crudo: la sesión de
    SQLAlchemy puede tener cacheado el valor viejo y el test pasaría sin
    comprobar nada."""
    rating, cantidad = db.session.execute(
        db.text("SELECT rating, resenas_count FROM productos WHERE id = :i"),
        {"i": producto_id},
    ).one()
    return (float(rating) if rating is not None else None, int(cantidad))


def _resenas_del_pedido(pedido_id) -> int:
    return db.session.execute(
        db.text("SELECT count(*) FROM resenas WHERE pedido_id = :p"),
        {"p": pedido_id},
    ).scalar_one()


def test_insertar_resena_queda_persistida_y_recalcula_stats(repo, usuario, producto):
    prod = producto()
    pedido_id = _pedido_con_producto(usuario, prod)

    creada = repo.crear(_resena(usuario.id, pedido_id, prod.id, 4))

    assert _resenas_del_pedido(pedido_id) == 1
    estrellas = db.session.execute(
        db.text("SELECT estrellas FROM resenas WHERE id = :i"), {"i": creada.id}
    ).scalar_one()
    assert int(estrellas) == 4
    assert _stats_producto(prod.id) == (4.0, 1), (
        "el INSERT no recalculó los stats del producto en la misma transacción"
    )


def test_el_triple_unico_se_traduce_a_duplicada_sin_inflar_stats(
    repo, usuario, producto
):
    """La violación del índice UNIQUE (doble submit, doble pestaña) tiene que
    llegar como `ResenaDuplicadaError` y con el rollback deshecho: ni la
    reseña original cambia ni el `rating` queda inflado por el intento."""
    prod = producto()
    pedido_id = _pedido_con_producto(usuario, prod)
    repo.crear(_resena(usuario.id, pedido_id, prod.id, 4))

    with pytest.raises(ResenaDuplicadaError):
        repo.crear(_resena(usuario.id, pedido_id, prod.id, 5))

    assert _resenas_del_pedido(pedido_id) == 1, (
        "el duplicado quedó persistido: el UNIQUE no está activo o el "
        "rollback no se ejecutó"
    )
    original = repo.obtener(
        UUID(str(usuario.id)), UUID(str(pedido_id)), UUID(str(prod.id))
    )
    assert original is not None and original.estrellas == 4, (
        "la reseña original cambió con el intento duplicado: debe ser inmutable"
    )
    assert _stats_producto(prod.id) == (4.0, 1), (
        "el intento duplicado infló los stats del producto"
    )
    # La sesión quedó utilizable tras el rollback: si no, el siguiente query
    # revienta con "current transaction is aborted".
    assert _resenas_del_pedido(pedido_id) == 1


def test_stats_con_una_y_dos_resenas_promedio_un_decimal(repo, usuario, producto):
    """R5: el promedio se recalcula por PRODUCTO (no por pedido). El mismo
    cliente comprando el mismo producto en dos pedidos distintos genera dos
    reseñas válidas (el triple las diferencia); 4 y luego 5 → 4.5 con count 2."""
    prod = producto()

    pedido_1 = _pedido_con_producto(usuario, prod)
    repo.crear(_resena(usuario.id, pedido_1, prod.id, 4))
    assert _stats_producto(prod.id) == (4.0, 1)

    pedido_2 = _pedido_con_producto(usuario, prod)
    repo.crear(_resena(usuario.id, pedido_2, prod.id, 5))
    assert _stats_producto(prod.id) == (4.5, 2), (
        "el promedio de 4 y 5 estrellas no quedó como 4.5 con count 2"
    )
