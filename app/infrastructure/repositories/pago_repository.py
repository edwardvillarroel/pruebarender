"""Repositorio de pagos (SQLAlchemy) con mapeo ORM -> dominio.

Implementa la interfaz `PagoRepository` de la capa de dominio. Los objetos que
cruzan la frontera son entidades `Pago`, nunca modelos ORM.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.domain.entities.pago import Pago
from app.domain.enums import EstadoPago
from app.domain.interfaces.repositories import PagoRepository as PagoRepositoryInterface
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.pago_model import PagoModel


class PagoRepository(PagoRepositoryInterface):
    model = PagoModel

    def get_by_id(self, entity_id: UUID) -> Pago | None:
        modelo = db.session.get(self.model, entity_id)
        return _a_entidad(modelo) if modelo else None

    def list(self, *filters: Any) -> list[Pago]:
        consulta = db.session.query(self.model)
        if filters:
            consulta = consulta.filter(*filters)
        return [_a_entidad(m) for m in consulta.all()]

    def get_by_token(self, token: str) -> Pago | None:
        modelo = db.session.execute(
            select(self.model).where(self.model.token == token)
        ).scalar_one_or_none()
        return _a_entidad(modelo) if modelo else None

    def get_by_pedido(self, pedido_id: UUID) -> Pago | None:
        modelo = db.session.execute(
            select(self.model)
            .where(self.model.pedido_id == pedido_id)
            .order_by(self.model.creado_en.desc())
        ).scalars().first()
        return _a_entidad(modelo) if modelo else None

    def add(self, entidad: Pago) -> Pago:
        db.session.add(_a_modelo(entidad))
        db.session.commit()
        return entidad

    def update(self, entidad: Pago) -> Pago:
        modelo = db.session.get(self.model, entidad.id)
        if modelo is None:
            raise ValueError("Pago no encontrado en BD")
        modelo.pedido_id = entidad.pedido_id
        modelo.monto = entidad.monto
        modelo.proveedor = entidad.proveedor
        modelo.token = entidad.token
        modelo.estado = entidad.estado.value
        db.session.commit()
        return entidad

    def delete(self, entidad: Pago) -> None:
        modelo = db.session.get(self.model, entidad.id)
        if modelo is None:
            raise ValueError("Pago no encontrado en BD")
        db.session.delete(modelo)
        db.session.commit()


def _a_entidad(modelo: PagoModel) -> Pago:
    return Pago(
        id=modelo.id,
        pedido_id=modelo.pedido_id,
        monto=modelo.monto,
        proveedor=modelo.proveedor,
        token=modelo.token,
        estado=EstadoPago(modelo.estado),
        creado_en=modelo.creado_en,
    )


def _a_modelo(entidad: Pago) -> PagoModel:
    return PagoModel(
        id=entidad.id,
        pedido_id=entidad.pedido_id,
        monto=entidad.monto,
        proveedor=entidad.proveedor,
        token=entidad.token,
        estado=entidad.estado.value,
        creado_en=entidad.creado_en,
    )