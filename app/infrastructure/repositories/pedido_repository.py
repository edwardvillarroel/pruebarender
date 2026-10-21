
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, exists, literal, select
from sqlalchemy.orm import selectinload

from app.domain.entities.detalle_pedido import DetallePedido
from app.domain.entities.pedido import Pedido
from app.domain.enums import EstadoPago, EstadoPedido
from app.domain.interfaces.repositories import (
    PedidoRepository as PedidoRepositoryInterface,
)
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.detalle_pedido_model import DetallePedidoModel
from app.infrastructure.database.models.pago_model import PagoModel
from app.infrastructure.database.models.pedido_model import PedidoModel
from app.infrastructure.database.models.producto_color_model import ProductoColorModel
from app.infrastructure.database.models.producto_model import ProductoModel
from app.infrastructure.database.models.resena_model import ResenaModel
from app.infrastructure.repositories.producto_repository import (
    RUTA_IMAGEN_COLOR,
    RUTA_IMAGEN_PRODUCTO,
    RUTA_THUMB_COLOR,
    RUTA_THUMB_PRODUCTO,
)


class PedidoRepository(PedidoRepositoryInterface):
    model = PedidoModel

    def get_by_id(self, entity_id: UUID) -> Pedido | None:
        modelo = db.session.execute(
            select(self.model)
            .options(selectinload(self.model.detalles))
            .where(self.model.id == entity_id)
        ).scalar_one_or_none()
        return self._con_imagenes([_a_entidad(modelo)])[0] if modelo else None

    def list(self, *filters: Any) -> list[Pedido]:
        consulta = db.session.query(self.model).options(
            selectinload(self.model.detalles)
        )
        if filters:
            consulta = consulta.filter(*filters)
        return self._con_imagenes([_a_entidad(m) for m in consulta.all()])

    def list_by_usuario(self, usuario_id: UUID) -> list[Pedido]:
        """Pedidos del usuario con `resenas_pendientes` (0|1) calculado en SQL.

        El badge es 1 solo si el pedido está `entregado` y existe al menos un
        detalle cuyo producto no tiene reseña de ESTE usuario en ESTE pedido.
        Una subquery en el mismo SELECT evita el N+1 de consultar reseñas
        pedido por pedido desde la ruta.
        """
        sin_resena_de_este = ~exists(
            select(literal(1))
            .select_from(ResenaModel)
            .where(ResenaModel.usuario_id == usuario_id)
            .where(ResenaModel.pedido_id == PedidoModel.id)
            .where(ResenaModel.producto_id == DetallePedidoModel.producto_id)
        )
        hay_producto_pendiente = exists(
            select(literal(1))
            .select_from(DetallePedidoModel)
            .where(DetallePedidoModel.pedido_id == PedidoModel.id)
            .where(sin_resena_de_este)
        )
        resenas_pendientes = case(
            (
                and_(
                    PedidoModel.estado == EstadoPedido.ENTREGADO.value,
                    hay_producto_pendiente,
                ),
                literal(1),
            ),
            else_=literal(0),
        ).label("resenas_pendientes")

        filas = db.session.execute(
            select(self.model, resenas_pendientes)
            .options(selectinload(self.model.detalles))
            .where(self.model.usuario_id == usuario_id)
            .order_by(self.model.creado_en.desc())
        ).all()
        pedidos = []
        for modelo, pendientes in filas:
            entidad = _a_entidad(modelo)
            entidad.resenas_pendientes = int(pendientes)
            pedidos.append(entidad)
        return self._con_imagenes(pedidos)

    def list_todos(self) -> list[Pedido]:
        modelos = db.session.execute(
            select(self.model)
            .options(selectinload(self.model.detalles))
            .order_by(self.model.creado_en.desc())
        ).scalars().all()
        return self._con_imagenes([_a_entidad(m) for m in modelos])

    def list_pagados(self) -> list[Pedido]:
        tiene_pago_completado = (
            select(literal(1))
            .select_from(PagoModel)
            .where(PagoModel.pedido_id == self.model.id)
            .where(PagoModel.estado == EstadoPago.COMPLETADO.value)
            .exists()
        )
        modelos = (
            db.session.query(self.model)
            .options(selectinload(self.model.detalles))
            .filter(tiene_pago_completado)
            .order_by(self.model.creado_en.desc())
            .all()
        )
        return self._con_imagenes([_a_entidad(m) for m in modelos])

    def _con_imagenes(self, pedidos: list[Pedido]) -> list[Pedido]:
        """Completa la foto de cada línea en UNA sola consulta (evita N+1).

        Los pedidos ya vienen con sus `detalles`, así que se juntan todos los
        ítems de todos los pedidos y se resuelven de una vez.
        """
        _resolver_imagenes([detalle for pedido in pedidos for detalle in pedido.detalles])
        return pedidos

    def crear_con_detalles(
        self, pedido: Pedido, detalles: list[DetallePedido]
    ) -> Pedido:
        modelo = PedidoModel(
            id=pedido.id,
            usuario_id=pedido.usuario_id,
            estado=pedido.estado.value,
            total=pedido.total,
            direccion_envio=pedido.direccion_envio,
            entrega=pedido.entrega,
            codigo_seguimiento=pedido.codigo_seguimiento,
            estado_seguimiento=pedido.estado_seguimiento,
            seguimiento_actualizado_en=pedido.seguimiento_actualizado_en,
            transportista=pedido.transportista,
            creado_en=pedido.creado_en,
        )
        for detalle in detalles:
            modelo.detalles.append(
                DetallePedidoModel(
                    id=detalle.id,
                    producto_id=detalle.producto_id,
                    cantidad=detalle.cantidad,
                    precio_unitario=detalle.precio_unitario,
                    color=detalle.color,
                    nombre=detalle.nombre,
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
        transportista: str | None = None,
    ) -> Pedido | None:
        modelo = db.session.get(self.model, pedido_id)
        if modelo is None:
            return None
        modelo.codigo_seguimiento = codigo_seguimiento
        modelo.transportista = transportista
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
        modelo.entrega = entidad.entrega
        modelo.codigo_seguimiento = entidad.codigo_seguimiento
        modelo.transportista = entidad.transportista
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


def _resolver_imagenes(detalles: list[DetallePedido]) -> None:
    """Completa `imagen` de cada detalle con la ruta pública del BLOB.

    Mismo criterio que `CarritoRepositoryBd._resolver_imagenes`: la foto del
    color elegido si esa variante tiene imagen, si no la del producto. Se
    resuelve en UNA sola consulta para todos los detalles (evita N+1) y solo se
    setea una URL cuando la imagen existe; si no, queda `None` y el frontend
    cae al icono genérico.
    """
    if not detalles:
        return

    ids = {detalle.producto_id for detalle in detalles}
    filas = db.session.execute(
        select(
            ProductoModel.id,
            ProductoModel.imagen_bytes.isnot(None).label("tiene_imagen"),
            ProductoColorModel.id.label("color_id"),
            ProductoColorModel.nombre.label("color_nombre"),
            ProductoColorModel.imagen_bytes.isnot(None).label("color_tiene_imagen"),
        )
        .outerjoin(
            ProductoColorModel, ProductoColorModel.producto_id == ProductoModel.id
        )
        .where(ProductoModel.id.in_(ids))
    ).all()

    productos = {f.id: f.tiene_imagen for f in filas}
    colores = {
        (f.id, (f.color_nombre or "").strip().lower()): (f.color_id, f.color_tiene_imagen)
        for f in filas
        if f.color_id is not None
    }

    for detalle in detalles:
        imagen = (
            RUTA_THUMB_PRODUCTO.format(producto_id=detalle.producto_id)
            if productos.get(detalle.producto_id)
            else None
        )
        if detalle.color:
            fila = colores.get((detalle.producto_id, detalle.color.strip().lower()))
            if fila and fila[1]:
                imagen = RUTA_THUMB_COLOR.format(color_id=fila[0])
        detalle.imagen = imagen


def _a_entidad(modelo: PedidoModel) -> Pedido:
    return Pedido(
        id=modelo.id,
        usuario_id=modelo.usuario_id,
        estado=EstadoPedido(modelo.estado),
        total=modelo.total,
        direccion_envio=modelo.direccion_envio,
        entrega=modelo.entrega,
        codigo_seguimiento=modelo.codigo_seguimiento,
        estado_seguimiento=modelo.estado_seguimiento,
        seguimiento_actualizado_en=modelo.seguimiento_actualizado_en,
        transportista=modelo.transportista,
        creado_en=modelo.creado_en,
        detalles=[
            DetallePedido(
                id=d.id,
                pedido_id=d.pedido_id,
                producto_id=d.producto_id,
                cantidad=d.cantidad,
                precio_unitario=d.precio_unitario,
                color=d.color,
                nombre=d.nombre,
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
        entrega=entidad.entrega,
        codigo_seguimiento=entidad.codigo_seguimiento,
        estado_seguimiento=entidad.estado_seguimiento,
        seguimiento_actualizado_en=entidad.seguimiento_actualizado_en,
        transportista=entidad.transportista,
        creado_en=entidad.creado_en,
    )
    modelo.detalles = [
        DetallePedidoModel(
            id=d.id,
            producto_id=d.producto_id,
            cantidad=d.cantidad,
            precio_unitario=d.precio_unitario,
            color=d.color,
            nombre=d.nombre,
        )
        for d in entidad.detalles
    ]
    return modelo