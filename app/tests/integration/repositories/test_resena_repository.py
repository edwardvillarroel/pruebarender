

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
    assert _resenas_del_pedido(pedido_id) == 1


def test_stats_con_una_y_dos_resenas_promedio_un_decimal(repo, usuario, producto):
    prod = producto()

    pedido_1 = _pedido_con_producto(usuario, prod)
    repo.crear(_resena(usuario.id, pedido_1, prod.id, 4))
    assert _stats_producto(prod.id) == (4.0, 1)

    pedido_2 = _pedido_con_producto(usuario, prod)
    repo.crear(_resena(usuario.id, pedido_2, prod.id, 5))
    assert _stats_producto(prod.id) == (4.5, 2), (
        "el promedio de 4 y 5 estrellas no quedó como 4.5 con count 2"
    )
