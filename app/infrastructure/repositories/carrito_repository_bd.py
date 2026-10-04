"""Repositorio del carrito persistido en la base de datos (Oracle/Postgres).

Implementa el mismo contrato que `CarritoRepositoryEnMemoria`; la capa de
aplicación no cambia, solo se sustituye la implementación en el punto de
composición (`create_app`). Un carrito pertenece a un usuario real: el
`usuario_id` viene del `sub` del JWT y debe existir en `usuarios`.
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.domain.entities.carrito import Carrito, ItemCarrito
from app.domain.interfaces.carrito_repository import CarritoRepository
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.carrito_model import CarritoItemModel, CarritoModel
from app.domain.time import utcnow


class CarritoRepositoryBd(CarritoRepository):
    """Carrito con respaldo en la base de datos.

    `carrito` y `carrito_items` exigen que el usuario (FK a `usuarios`) y el
    producto (FK a `productos`) existan. Si el producto no existe, el INSERT
    falla con `IntegrityError` (se hace rollback y se relanza para que la capa
    de API lo traduzca a un mensaje al cliente).
    """

    def obtener(self, usuario_id: str) -> Carrito | None:
        modelo = self._buscar(usuario_id)
        if modelo is None:
            return None
        return Carrito(
            usuario_id=str(modelo.usuario_id),
            actualizado_en=modelo.actualizado_en,
            items=[
                ItemCarrito(
                    id=item.id,
                    producto_id=str(item.producto_id),
                    cantidad=item.cantidad,
                    color=item.color,
                    agregado_en=item.agregado_en,
                )
                for item in modelo.items
            ],
        )

    def guardar(self, carrito: Carrito) -> Carrito:
        uid = _a_uuid(carrito.usuario_id)
        ahora = utcnow()
        modelo = self._buscar(uid)

        if modelo is None:
            modelo = CarritoModel(
                id=uuid.uuid4(),
                usuario_id=uid,
                creado_en=ahora,
                actualizado_en=ahora,
            )
            db.session.add(modelo)
        else:
            modelo.actualizado_en = ahora

        ids_presentes = {item.id for item in carrito.items}
        for item_m in list(modelo.items):
            if item_m.id not in ids_presentes:
                db.session.delete(item_m)

        existentes = {item_m.id: item_m for item_m in modelo.items}
        for item in carrito.items:
            item_m = existentes.get(item.id)
            if item_m is None:
                db.session.add(
                    CarritoItemModel(
                        id=item.id,
                        carrito=modelo,
                        producto_id=_a_uuid(item.producto_id),
                        cantidad=item.cantidad,
                        color=item.color,
                        agregado_en=item.agregado_en or ahora,
                    )
                )
            else:
                item_m.cantidad = item.cantidad
                item_m.color = item.color

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise
        return carrito

    def eliminar(self, usuario_id: str) -> None:
        modelo = self._buscar(usuario_id)
        if modelo is None:
            return
        db.session.delete(modelo)
        db.session.commit()

    def _buscar(self, usuario_id: str) -> CarritoModel | None:
        return db.session.execute(
            select(CarritoModel)
            .options(selectinload(CarritoModel.items))
            .where(CarritoModel.usuario_id == _a_uuid(usuario_id))
        ).scalar_one_or_none()


def _a_uuid(valor: str) -> uuid.UUID:
    return uuid.UUID(str(valor))
