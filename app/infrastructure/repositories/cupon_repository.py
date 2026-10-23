from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.domain.entities.cupon import Cupon
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.cupon_model import CuponModel


class CuponRepository:
    def listar(self) -> list[Cupon]:
        modelos = CuponModel.query.order_by(CuponModel.creado_en.desc()).all()
        return [self._a_entidad(m) for m in modelos]

    def get_by_codigo(self, codigo: str) -> Cupon | None:
        modelo = CuponModel.query.filter_by(codigo=codigo.upper().strip()).first()
        return self._a_entidad(modelo) if modelo else None

    def get_by_id(self, cupon_id: UUID) -> Cupon | None:
        modelo = db.session.get(CuponModel, cupon_id)
        return self._a_entidad(modelo) if modelo else None

    def crear(self, cupon: Cupon) -> Cupon:
        modelo = CuponModel(
            id=cupon.id,
            codigo=cupon.codigo.upper().strip(),
            tipo=cupon.tipo,
            valor=Decimal(str(cupon.valor)),
            activo=cupon.activo,
            uso_unico=cupon.uso_unico,
            usado=cupon.usado,
            usado_por=cupon.usado_por,
            usado_en=cupon.usado_en,
            creado_por=cupon.creado_por,
            descripcion=cupon.descripcion,
        )
        db.session.add(modelo)
        db.session.commit()
        db.session.refresh(modelo)
        return self._a_entidad(modelo)

    def marcar_usado(self, cupon: Cupon, usuario_id: UUID) -> Cupon:
        modelo = db.session.get(CuponModel, cupon.id)
        if modelo is None:
            raise ValueError("Cupón no encontrado")
        modelo.usado = True
        modelo.usado_por = usuario_id
        modelo.usado_en = datetime.utcnow()
        if modelo.uso_unico:
            modelo.activo = False
        db.session.commit()
        db.session.refresh(modelo)
        return self._a_entidad(modelo)

    def liberar(self, cupon: Cupon, usuario_id: UUID) -> Cupon:
        """Devuelve un cupón usado por un pedido cuyo pago nunca se completó.

        Solo se libera si el cupón lo consumió el mismo usuario: si lo usó otro,
        el cupón no es de este pedido y no se toca.
        """
        modelo = db.session.get(CuponModel, cupon.id)
        if modelo is None:
            raise ValueError("Cupón no encontrado")
        if modelo.usado_por != usuario_id:
            return cupon
        modelo.usado = False
        modelo.usado_por = None
        modelo.usado_en = None
        if modelo.uso_unico:
            modelo.activo = True
        db.session.commit()
        db.session.refresh(modelo)
        return self._a_entidad(modelo)

    def eliminar(self, cupon_id: UUID) -> None:
        modelo = db.session.get(CuponModel, cupon_id)
        if modelo is None:
            raise ValueError("Cupón no encontrado")
        db.session.delete(modelo)
        db.session.commit()

    @staticmethod
    def _a_entidad(modelo: CuponModel) -> Cupon:
        return Cupon(
            id=modelo.id,
            codigo=modelo.codigo,
            tipo=modelo.tipo,
            valor=float(modelo.valor),
            activo=modelo.activo,
            uso_unico=modelo.uso_unico,
            usado=modelo.usado,
            usado_por=modelo.usado_por,
            usado_en=modelo.usado_en,
            creado_por=modelo.creado_por,
            descripcion=modelo.descripcion,
            creado_en=modelo.creado_en,
        )
