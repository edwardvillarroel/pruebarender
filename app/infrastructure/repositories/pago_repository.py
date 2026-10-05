"""Repositorio de pagos (SQLAlchemy) con mapeo ORM -> dominio.

Implementa la interfaz `PagoRepository` de la capa de dominio. Los objetos que
cruzan la frontera son entidades `Pago`, nunca modelos ORM.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.domain.entities.pago import Pago
from app.domain.enums import EstadoPago
from app.domain.interfaces.repositories import (
    ClaveIdempotenciaOcupada,
    PagoRepository as PagoRepositoryInterface,
)
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

    def get_by_clave_idempotencia(self, clave: str) -> Pago | None:
        """Pago vivo de la clave; si ya no hay, el mas reciente de esa clave.

        El indice `idx_pago_idempotencia` es parcial (`estado = 'pendiente'`),
        asi que la clave puede aparecer en varias filas a lo largo del tiempo:
        primero se busca el pendiente, que es al que un reintento tiene que
        devolverle la URL, y solo si no hay ninguno se cae al mas reciente para
        que el caso de uso pueda explicar que la operacion ya concluyo.
        """
        vivo = db.session.execute(
            select(self.model)
            .where(self.model.clave_idempotencia == clave)
            .where(self.model.estado == EstadoPago.PENDIENTE.value)
            .order_by(self.model.creado_en.desc())
        ).scalars().first()
        if vivo is not None:
            return _a_entidad(vivo)
        cualquiera = db.session.execute(
            select(self.model)
            .where(self.model.clave_idempotencia == clave)
            .order_by(self.model.creado_en.desc())
        ).scalars().first()
        return _a_entidad(cualquiera) if cualquiera else None

    def add(self, entidad: Pago) -> Pago:
        try:
            db.session.add(_a_modelo(entidad))
            db.session.commit()
        except IntegrityError:
            # El rollback va SIEMPRE, no solo por la idempotencia: despues de
            # un error de integridad la sesion queda abortada y cualquier
            # consulta posterior revienta con "current transaction is aborted".
            db.session.rollback()
            # Si el choque fue con el indice parcial de idempotencia, es la
            # carrera del doble click: se informa con la excepcion del dominio.
            # Cualquier otro error de integridad (FK, CHECK) se propaga tal
            # cual, porque no es un conflicto de claves y hiding seria peor.
            if entidad.clave_idempotencia is not None and self.get_by_clave_idempotencia(
                entidad.clave_idempotencia
            ) is not None:
                raise ClaveIdempotenciaOcupada(
                    f"Ya hay un pago pendiente con esa clave de idempotencia"
                ) from None
            raise
        return entidad

    def update(self, entidad: Pago) -> Pago:
        modelo = db.session.get(self.model, entidad.id)
        if modelo is None:
            raise ValueError("Pago no encontrado en BD")
        modelo.pedido_id = entidad.pedido_id
        modelo.monto = entidad.monto
        modelo.proveedor = entidad.proveedor
        modelo.token = entidad.token
        modelo.clave_idempotencia = entidad.clave_idempotencia
        modelo.url_intento = entidad.url_intento
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
        clave_idempotencia=modelo.clave_idempotencia,
        url_intento=modelo.url_intento,
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
        clave_idempotencia=entidad.clave_idempotencia,
        url_intento=entidad.url_intento,
        estado=entidad.estado.value,
        creado_en=entidad.creado_en,
    )