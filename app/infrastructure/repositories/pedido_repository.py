"""Repositorio de pedidos (SQLAlchemy) con mapeo ORM -> dominio.

Implementa la interfaz `PedidoRepository` de la capa de dominio. Los objetos
que cruzan la frontera de infraestructura son siempre entidades `Pedido` y
`DetallePedido`, nunca modelos ORM. La persistencia de `detalle_pedidos` ocurre
en la misma transacción que el pedido (`crear_con_detalles`).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.domain.entities.detalle_pedido import DetallePedido
from app.domain.entities.pedido import Pedido
from app.domain.enums import EstadoPedido
from app.domain.interfaces.repositories import (
    PedidoRepository as PedidoRepositoryInterface,
)
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.detalle_pedido_model import DetallePedidoModel
from app.infrastructure.database.models.pedido_model import PedidoModel


class PedidoRepository(PedidoRepositoryInterface):
    model = PedidoModel

    def get_by_id(self, entity_id: UUID) -> Pedido | None:
        modelo = db.session.execute(
            select(self.model)
            .options(selectinload(self.model.detalles))
            .where(self.model.id == entity_id)
        ).scalar_one_or_none()
        return _a_entidad(modelo) if modelo else None

    def list(self, *filters: Any) -> list[Pedido]:
        consulta = db.session.query(self.model).options(
            selectinload(self.model.detalles)
        )
        if filters:
            consulta = consulta.filter(*filters)
        return [_a_entidad(m) for m in consulta.all()]

    def list_by_usuario(self, usuario_id: UUID) -> list[Pedido]:
        modelos = db.session.execute(
            select(self.model)
            .options(selectinload(self.model.detalles))
            .where(self.model.usuario_id == usuario_id)
            .order_by(self.model.creado_en.desc())
        ).scalars().all()
        return [_a_entidad(m) for m in modelos]

    def list_todos(self) -> list[Pedido]:
        modelos = db.session.execute(
            select(self.model)
            .options(selectinload(self.model.detalles))
            .order_by(self.model.creado_en.desc())
        ).scalars().all()
        return [_a_entidad(m) for m in modelos]

    def crear_con_detalles(
        self, pedido: Pedido, detalles: list[DetallePedido]
    ) -> Pedido:
        modelo = PedidoModel(
            id=pedido.id,
            usuario_id=pedido.usuario_id,
            estado=pedido.estado.value,
            total=pedido.total,
            direccion_envio=pedido.direccion_envio,
            codigo_seguimiento=pedido.codigo_seguimiento,
            estado_seguimiento=pedido.estado_seguimiento,
            seguimiento_actualizado_en=pedido.seguimiento_actualizado_en,
            creado_en=pedido.creado_en,
        )
        for detalle in detalles:
            modelo.detalles.append(
                DetallePedidoModel(
                    id=detalle.id,
                    producto_id=detalle.producto_id,
                    cantidad=detalle.cantidad,
                    precio_unitario=detalle.precio_unitario,
                )
            )
        db.session.add(modelo)
        db.session.commit()
        return pedido

    def actualizar_estado(
        self, pedido_id: UUID, estado: EstadoPedido
    ) -> Pedido | None:
        modelo = db.session.get(self.model, pedido_id)
        if modelo is None:
            return None
        modelo.estado = estado.value
        db.session.commit()
        return _a_entidad(modelo)

    def actualizar_seguimiento(
        self,
        pedido_id: UUID,
        codigo_seguimiento: str | None,
        estado_seguimiento: str | None,
        actualizado_en: datetime | None,
    ) -> Pedido | None:
        modelo = db.session.get(self.model, pedido_id)
        if modelo is None:
            return None
        modelo.codigo_seguimiento = codigo_seguimiento
        modelo.estado_seguimiento = estado_seguimiento
        modelo.seguimiento_actualizado_en = actualizado_en
        db.session.commit()
        return _a_entidad(modelo)

    def add(self, entidad: Pedido) -> Pedido:
        db.session.add(_a_modelo(entidad))
        db.session.commit()
        return entidad

    def update(self, entidad: Pedido) -> Pedido:
        modelo = db.session.get(self.model, entidad.id)
        if modelo is None:
            raise ValueError("Pedido no encontrado en BD")
        modelo.usuario_id = entidad.usuario_id
        modelo.estado = entidad.estado.value
        modelo.total = entidad.total
        modelo.direccion_envio = entidad.direccion_envio
        modelo.codigo_seguimiento = entidad.codigo_seguimiento
        modelo.estado_seguimiento = entidad.estado_seguimiento
        modelo.seguimiento_actualizado_en = entidad.seguimiento_actualizado_en
        db.session.commit()
        return entidad

    def delete(self, entidad: Pedido) -> None:
        modelo = db.session.get(self.model, entidad.id)
        if modelo is None:
            raise ValueError("Pedido no encontrado en BD")
        db.session.delete(modelo)
        db.session.commit()


def _a_entidad(modelo: PedidoModel) -> Pedido:
    return Pedido(
        id=modelo.id,
        usuario_id=modelo.usuario_id,
        estado=EstadoPedido(modelo.estado),
        total=modelo.total,
        direccion_envio=modelo.direccion_envio,
        codigo_seguimiento=modelo.codigo_seguimiento,
        estado_seguimiento=modelo.estado_seguimiento,
        seguimiento_actualizado_en=modelo.seguimiento_actualizado_en,
        creado_en=modelo.creado_en,
        detalles=[
            DetallePedido(
                id=d.id,
                pedido_id=d.pedido_id,
                producto_id=d.producto_id,
                cantidad=d.cantidad,
                precio_unitario=d.precio_unitario,
            )
            for d in modelo.detalles
        ],
    )


def _a_modelo(entidad: Pedido) -> PedidoModel:
    modelo = PedidoModel(
        id=entidad.id,
        usuario_id=entidad.usuario_id,
        estado=entidad.estado.value,
        total=entidad.total,
        direccion_envio=entidad.direccion_envio,
        codigo_seguimiento=entidad.codigo_seguimiento,
        estado_seguimiento=entidad.estado_seguimiento,
        seguimiento_actualizado_en=entidad.seguimiento_actualizado_en,
        creado_en=entidad.creado_en,
    )
    modelo.detalles = [
        DetallePedidoModel(
            id=d.id,
            producto_id=d.producto_id,
            cantidad=d.cantidad,
            precio_unitario=d.precio_unitario,
        )
        for d in entidad.detalles
    ]
    return modelo