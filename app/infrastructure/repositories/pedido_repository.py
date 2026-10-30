
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, exists, func, literal, select
from sqlalchemy.orm import selectinload

from app.domain.entities.detalle_pedido import DetallePedido
from app.domain.entities.pedido import Pedido
from app.domain.enums import EstadoPago, EstadoPedido, TipoDocumentoTributario
from app.domain.time import utcnow
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
        fila = db.session.execute(
            select(self.model, self._estado_pago().label("estado_pago"))
            .options(selectinload(self.model.detalles))
            .where(self.model.id == entity_id)
        ).one_or_none()
        return self._con_estado_pago([fila])[0] if fila else None

    def get_by_cotizacion(self, cotizacion_id: UUID) -> Pedido | None:
        fila = db.session.execute(
            select(self.model, self._estado_pago().label("estado_pago"))
            .options(selectinload(self.model.detalles))
            .where(self.model.cotizacion_id == cotizacion_id)
        ).one_or_none()
        return self._con_estado_pago([fila])[0] if fila else None

    def pagos_por_cotizacion(
        self, cotizacion_ids: list[UUID]
    ) -> dict[UUID, dict[str, Any]]:
        """Estado de pago de varias cotizaciones en una sola consulta."""
        if not cotizacion_ids:
            return {}
        filas = db.session.execute(
            select(PedidoModel.cotizacion_id, PedidoModel.id, PagoModel.estado)
            .outerjoin(PagoModel, PagoModel.pedido_id == PedidoModel.id)
            .where(PedidoModel.cotizacion_id.in_(cotizacion_ids))
        ).all()
        resultado: dict[UUID, dict[str, Any]] = {}
        for cotizacion_id, pedido_id, estado_pago in filas:
            actual = resultado.setdefault(
                cotizacion_id,
                {"pedido_id": str(pedido_id), "pagada": False},
            )
            if estado_pago == EstadoPago.COMPLETADO.value:
                actual["pagada"] = True
        return resultado

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
            .where(DetallePedidoModel.producto_id.isnot(None))
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

        resenas_completadas = (
            select(func.count())
            .select_from(ResenaModel)
            .where(ResenaModel.usuario_id == usuario_id)
            .where(ResenaModel.pedido_id == PedidoModel.id)
            .correlate(PedidoModel)
            .scalar_subquery()
            .label("resenas_completadas")
        )

        filas = db.session.execute(
            select(
                self.model,
                resenas_pendientes,
                resenas_completadas,
                self._estado_pago().label("estado_pago"),
            )
            .options(selectinload(self.model.detalles))
            .where(self.model.usuario_id == usuario_id)
            .order_by(self.model.creado_en.desc())
        ).all()
        pedidos = []
        for modelo, pendientes, completadas, estado_pago in filas:
            entidad = _a_entidad(modelo)
            entidad.resenas_pendientes = int(pendientes)
            entidad.resenas_completadas = int(completadas)
            entidad.estado_pago = estado_pago
            pedidos.append(entidad)
        return self._con_imagenes(pedidos)

    def list_todos(self) -> list[Pedido]:
        """Todos los pedidos, con el estado de su pago."""
        filas = db.session.execute(
            select(self.model, self._estado_pago().label("estado_pago"))
            .options(selectinload(self.model.detalles))
            .order_by(self.model.creado_en.desc())
        ).all()
        return self._con_estado_pago(filas)

    def list_pagados(self) -> list[Pedido]:
        tiene_pago_completado = (
            select(literal(1))
            .select_from(PagoModel)
            .where(PagoModel.pedido_id == self.model.id)
            .where(PagoModel.estado == EstadoPago.COMPLETADO.value)
            .exists()
        )
        filas = db.session.execute(
            select(self.model, self._estado_pago().label("estado_pago"))
            .options(selectinload(self.model.detalles))
            .filter(tiene_pago_completado)
            .order_by(self.model.creado_en.desc())
        ).all()
        return self._con_estado_pago(filas)

    def _estado_pago(self):
        """Estado del pago del pedido: el completado si existe; si no, el último.

        Se resuelve en SQL para no consultar el pago de cada pedido (N+1).
        Devuelve `None` para pedidos sin ningún intento de pago.
        """
        return (
            select(PagoModel.estado)
            .where(PagoModel.pedido_id == self.model.id)
            .order_by(
                case((PagoModel.estado == EstadoPago.COMPLETADO.value, 0), else_=1),
                PagoModel.creado_en.desc(),
            )
            .limit(1)
            .correlate(self.model)
            .scalar_subquery()
        )

    def _con_estado_pago(self, filas) -> list[Pedido]:
        pedidos = []
        for modelo, estado_pago in filas:
            entidad = _a_entidad(modelo)
            entidad.estado_pago = estado_pago
            pedidos.append(entidad)
        return self._con_imagenes(pedidos)

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
            cotizacion_id=pedido.cotizacion_id,
            estado=pedido.estado.value,
            total=pedido.total,
            subtotal=pedido.subtotal,
            descuento_productos=pedido.descuento_productos,
            descuento_cupon=pedido.descuento_cupon,
            cupon_codigo=pedido.cupon_codigo,
            direccion_envio=pedido.direccion_envio,
            entrega=pedido.entrega,
            tipo_documento=_valor_tipo_documento(pedido.tipo_documento),
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
                    precio_original=detalle.precio_original,
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

    def marcar_aviso_cancelacion(self, pedido_id: UUID) -> Pedido | None:
        """Enciende el aviso de anulacion aceptada por Tuu (badge del cliente)."""
        modelo = db.session.get(self.model, pedido_id)
        if modelo is None:
            return None
        modelo.aviso_cancelacion_en = utcnow()
        modelo.aviso_cancelacion_visto = False
        db.session.commit()
        return _a_entidad(modelo)

    def marcar_aviso_cancelacion_visto(self, pedido_id: UUID) -> Pedido | None:
        """Apaga el badge: el cliente ya abrio el aviso."""
        modelo = db.session.get(self.model, pedido_id)
        if modelo is None:
            return None
        modelo.aviso_cancelacion_visto = True
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
        modelo.cotizacion_id = entidad.cotizacion_id
        modelo.estado = entidad.estado.value
        modelo.total = entidad.total
        modelo.subtotal = entidad.subtotal
        modelo.descuento_productos = entidad.descuento_productos
        modelo.descuento_cupon = entidad.descuento_cupon
        modelo.cupon_codigo = entidad.cupon_codigo
        modelo.direccion_envio = entidad.direccion_envio
        modelo.entrega = entidad.entrega
        modelo.tipo_documento = _valor_tipo_documento(entidad.tipo_documento)
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

    ids = {
        detalle.producto_id
        for detalle in detalles
        if detalle.producto_id is not None
    }
    if not ids:
        for detalle in detalles:
            detalle.imagen = None
        return

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


def _valor_tipo_documento(tipo) -> str | None:
    """El enum del tipo de documento, como texto para la columna."""
    if tipo is None:
        return None
    if isinstance(tipo, TipoDocumentoTributario):
        return tipo.value
    return str(tipo)


def _a_tipo_documento(valor) -> TipoDocumentoTributario | None:
    """La columna de texto, como enum del dominio."""
    if not valor:
        return None
    try:
        return TipoDocumentoTributario(str(valor))
    except ValueError:
        return None


def _a_entidad(modelo: PedidoModel) -> Pedido:
    return Pedido(
        id=modelo.id,
        usuario_id=modelo.usuario_id,
        cotizacion_id=modelo.cotizacion_id,
        estado=EstadoPedido(modelo.estado),
        total=modelo.total,
        subtotal=modelo.subtotal,
        descuento_productos=modelo.descuento_productos,
        descuento_cupon=modelo.descuento_cupon,
        cupon_codigo=modelo.cupon_codigo,
        direccion_envio=modelo.direccion_envio,
        entrega=modelo.entrega,
        tipo_documento=_a_tipo_documento(modelo.tipo_documento),
        codigo_seguimiento=modelo.codigo_seguimiento,
        estado_seguimiento=modelo.estado_seguimiento,
        seguimiento_actualizado_en=modelo.seguimiento_actualizado_en,
        transportista=modelo.transportista,
        aviso_cancelacion_en=modelo.aviso_cancelacion_en,
        aviso_cancelacion_visto=bool(modelo.aviso_cancelacion_visto),
        creado_en=modelo.creado_en,
        detalles=[
            DetallePedido(
                id=d.id,
                pedido_id=d.pedido_id,
                producto_id=d.producto_id,
                cantidad=d.cantidad,
                precio_unitario=d.precio_unitario,
                precio_original=d.precio_original,
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
        cotizacion_id=entidad.cotizacion_id,
        estado=entidad.estado.value,
        total=entidad.total,
        subtotal=entidad.subtotal,
        descuento_productos=entidad.descuento_productos,
        descuento_cupon=entidad.descuento_cupon,
        cupon_codigo=entidad.cupon_codigo,
        direccion_envio=entidad.direccion_envio,
        entrega=entidad.entrega,
        tipo_documento=_valor_tipo_documento(entidad.tipo_documento),
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
            precio_original=d.precio_original,
            color=d.color,
            nombre=d.nombre,
        )
        for d in entidad.detalles
    ]
    return modelo