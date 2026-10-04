"""Repositorio de venta local (SQLAlchemy) con mapeo ORM -> dominio.

Implementa la interfaz `VentaLocalRepository` de la capa de dominio. Los objetos
que cruzan la frontera de infraestructura son siempre entidades (`SesionVenta`,
`VentaLocal`), no modelos ORM.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.domain.entities.venta_local import SesionVenta, VentaLocal, VentaLocalItem
from app.domain.interfaces.venta_local_repository import (
    VentaLocalRepository as VentaLocalRepositoryInterface,
)
from app.domain.time import utcnow
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.producto_model import ProductoModel
from app.infrastructure.database.models.venta_local_model import (
    SesionVentaModel,
    VentaLocalItemModel,
    VentaLocalModel,
)


class VentaLocalRepository(VentaLocalRepositoryInterface):
    def crear_sesion(self, sesion: SesionVenta) -> SesionVenta:
        modelo = _a_modelo_sesion(sesion)
        db.session.add(modelo)
        db.session.commit()
        db.session.refresh(modelo)
        return _a_entidad_sesion(modelo)

    def obtener_sesion_por_id(self, sesion_id: UUID) -> SesionVenta | None:
        modelo = db.session.execute(
            select(SesionVentaModel).where(SesionVentaModel.id == sesion_id)
        ).scalar_one_or_none()
        return _a_entidad_sesion(modelo) if modelo else None

    def obtener_sesion_abierta_de(self, usuario_id: UUID) -> SesionVenta | None:
        modelo = db.session.execute(
            select(SesionVentaModel).where(
                SesionVentaModel.usuario_id == usuario_id,
                SesionVentaModel.estado == "abierta",
            )
        ).scalar_one_or_none()
        return _a_entidad_sesion(modelo) if modelo else None

    def registrar_venta(self, venta: VentaLocal) -> VentaLocal:
        # Descuenta stock atómicamente y persiste la venta + items en UNA transacción.
        # Cada UPDATE con guard stock >= cantidad protege contra stock agotado entre validación y persistencia.
        for item in venta.items:
            resultado = db.session.execute(
                update(ProductoModel)
                .where(
                    ProductoModel.id == item.producto_id,
                    ProductoModel.stock >= item.cantidad,
                )
                .values(stock=ProductoModel.stock - item.cantidad)
            )
            if resultado.rowcount == 0:
                db.session.rollback()
                raise ValueError(
                    f"No hay stock suficiente de «{item.nombre}» (disponible: {producto_disponible(item.producto_id)})"
                )
        modelo = _a_modelo_venta(venta)
        db.session.add(modelo)
        db.session.commit()
        db.session.refresh(modelo)
        return _a_entidad_venta(modelo)

    def cerrar_sesion(self, sesion_id: UUID) -> SesionVenta | None:
        modelo = db.session.get(SesionVentaModel, sesion_id)
        if modelo is None:
            return None
        modelo.estado = "cerrada"
        modelo.cerrada_en = utcnow()
        db.session.commit()
        return _a_entidad_sesion(modelo)

    def listar_reportes(self, usuario_id: UUID | None = None) -> list[SesionVenta]:
        consulta = (
            select(SesionVentaModel)
            .options(selectinload(SesionVentaModel.ventas))
            .where(SesionVentaModel.estado == "cerrada")
            .order_by(SesionVentaModel.fecha.desc(), SesionVentaModel.creado_en.desc())
        )
        if usuario_id is not None:
            consulta = consulta.where(SesionVentaModel.usuario_id == usuario_id)
        modelos = db.session.execute(consulta).scalars().all()
        return [_a_entidad_sesion(m) for m in modelos]

    def obtener_reporte(self, sesion_id: UUID) -> SesionVenta | None:
        modelo = db.session.execute(
            select(SesionVentaModel)
            .options(selectinload(SesionVentaModel.ventas))
            .where(
                SesionVentaModel.id == sesion_id,
                SesionVentaModel.estado == "cerrada",
            )
        ).scalar_one_or_none()
        return _a_entidad_sesion(modelo) if modelo else None

    def obtener_ventas_de_sesion(self, sesion_id: UUID) -> list[VentaLocal]:
        modelos = db.session.execute(
            select(VentaLocalModel)
            .options(selectinload(VentaLocalModel.items))
            .where(VentaLocalModel.sesion_id == sesion_id)
            .order_by(VentaLocalModel.creado_en)
        ).scalars().all()
        return [_a_entidad_venta(m) for m in modelos]


def _a_entidad_sesion(modelo: SesionVentaModel) -> SesionVenta:
    return SesionVenta(
        id=modelo.id,
        lugar=modelo.lugar,
        fecha=modelo.fecha,
        usuario_id=modelo.usuario_id,
        estado=modelo.estado,
        creado_en=modelo.creado_en,
        cerrada_en=modelo.cerrada_en,
    )


def producto_disponible(producto_id: UUID) -> int:
    """Stock actual del producto para un mensaje de error (consulta previa al flush cruzado)."""
    stock = db.session.execute(
        select(ProductoModel.stock).where(ProductoModel.id == producto_id)
    ).scalar_one_or_none()
    return int(stock) if stock is not None else 0


def _a_entidad_venta(modelo: VentaLocalModel) -> VentaLocal:
    return VentaLocal(
        id=modelo.id,
        sesion_id=modelo.sesion_id,
        medio_pago=modelo.medio_pago,
        total=modelo.total,
        creado_en=modelo.creado_en,
        items=[_a_entidad_item(i) for i in modelo.items],
    )


def _a_entidad_item(modelo: VentaLocalItemModel) -> VentaLocalItem:
    return VentaLocalItem(
        id=modelo.id,
        venta_id=modelo.venta_id,
        producto_id=modelo.producto_id,
        nombre=modelo.nombre,
        cantidad=modelo.cantidad,
        precio_unitario=modelo.precio_unitario,
    )


def _a_modelo_sesion(entidad: SesionVenta) -> SesionVentaModel:
    return SesionVentaModel(
        id=entidad.id,
        lugar=entidad.lugar,
        fecha=entidad.fecha,
        usuario_id=entidad.usuario_id,
        estado=entidad.estado,
        creado_en=entidad.creado_en,
        cerrada_en=entidad.cerrada_en,
    )


def _a_modelo_venta(entidad: VentaLocal) -> VentaLocalModel:
    return VentaLocalModel(
        id=entidad.id,
        sesion_id=entidad.sesion_id,
        medio_pago=entidad.medio_pago,
        total=entidad.total,
        creado_en=entidad.creado_en,
        items=[
            VentaLocalItemModel(
                id=item.id,
                venta_id=entidad.id,
                producto_id=item.producto_id,
                nombre=item.nombre,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
            )
            for item in entidad.items
        ],
    )
