
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.domain.entities.carrito import Carrito, ItemCarrito
from app.domain.interfaces.carrito_repository import CarritoRepository
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.carrito_model import CarritoItemModel, CarritoModel
from app.infrastructure.database.models.producto_color_model import ProductoColorModel
from app.infrastructure.database.models.producto_model import ProductoModel
from app.infrastructure.repositories.producto_repository import (
    RUTA_IMAGEN_COLOR,
    RUTA_IMAGEN_PRODUCTO,
)
from app.domain.time import utcnow


class CarritoRepositoryBd(CarritoRepository):
    def obtener(self, usuario_id: str) -> Carrito | None:
        modelo = self._buscar(usuario_id)
        if modelo is None:
            return None
        items = [
            ItemCarrito(
                id=item.id,
                producto_id=str(item.producto_id),
                cantidad=item.cantidad,
                color=item.color,
                agregado_en=item.agregado_en,
            )
            for item in modelo.items
        ]
        self._resolver_imagenes(items)
        return Carrito(
            usuario_id=str(modelo.usuario_id),
            actualizado_en=modelo.actualizado_en,
            items=items,
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
        self._resolver_imagenes(carrito.items)
        return carrito

    def eliminar(self, usuario_id: str) -> None:
        modelo = self._buscar(usuario_id)
        if modelo is None:
            return
        db.session.delete(modelo)
        db.session.commit()

    def _resolver_imagenes(self, items: list[ItemCarrito]) -> None:
        if not items:
            return

        ids = {_a_uuid(item.producto_id) for item in items}
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

        for item in items:
            producto_id = _a_uuid(item.producto_id)
            imagen = (
                RUTA_IMAGEN_PRODUCTO.format(producto_id=producto_id)
                if productos.get(producto_id)
                else None
            )
            if item.color:
                fila = colores.get((producto_id, item.color.strip().lower()))
                if fila and fila[1]:
                    imagen = RUTA_IMAGEN_COLOR.format(color_id=fila[0])
            item.imagen = imagen

    def _buscar(self, usuario_id: str) -> CarritoModel | None:
        return db.session.execute(
            select(CarritoModel)
            .options(selectinload(CarritoModel.items))
            .where(CarritoModel.usuario_id == _a_uuid(usuario_id))
        ).scalar_one_or_none()


def _a_uuid(valor: str) -> uuid.UUID:
    return uuid.UUID(str(valor))
