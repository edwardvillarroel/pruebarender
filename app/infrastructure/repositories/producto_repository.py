"""Repositorio de productos (SQLAlchemy) con mapeo ORM -> dominio.

Implementa la interfaz `ProductoRepository` de la capa de dominio. Los objetos
que cruzan la frontera de infraestructura son siempre entidades `Producto`, no
modelos ORM.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.domain.entities.producto import ImagenProducto, Producto
from app.domain.interfaces.repositories import (
    ProductoRepository as ProductoRepositoryInterface,
)
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.producto_model import ProductoModel


class ProductoRepository(ProductoRepositoryInterface):
    model = ProductoModel

    def get_by_id(self, entity_id: UUID) -> Producto | None:
        modelo = db.session.get(self.model, entity_id)
        return _a_entidad(modelo) if modelo else None

    def list(self, *filters: Any) -> list[Producto]:
        consulta = db.session.query(self.model)
        if filters:
            consulta = consulta.filter(*filters)
        return [_a_entidad(m) for m in consulta.all()]

    def get_by_categoria(self, categoria_id: UUID) -> list[Producto]:
        return self._ejecutar(
            select(self.model).where(self.model.categoria_id == categoria_id)
        )

    def list_activos(self) -> list[Producto]:
        return self._ejecutar(
            select(self.model)
            .where(self.model.activo == True)  # noqa: E712 - Oracle: activo = 1
            .order_by(self.model.nombre)
        )

    def get_imagen_by_id(self, producto_id: UUID) -> ImagenProducto | None:
        fila = db.session.execute(
            select(self.model.imagen_bytes, self.model.imagen_content_type).where(
                self.model.id == producto_id
            )
        ).first()
        if fila is None or fila.imagen_bytes is None:
            return None
        return ImagenProducto(bytes=fila.imagen_bytes, content_type=fila.imagen_content_type)

    def add(self, entidad: Producto) -> Producto:
        db.session.add(_a_modelo(entidad))
        db.session.commit()
        return entidad

    def update(self, entidad: Producto) -> Producto:
        modelo = db.session.get(self.model, entidad.id)
        if modelo is None:
            raise ValueError("Producto no encontrado en BD")
        modelo.nombre = entidad.nombre
        modelo.descripcion = entidad.descripcion
        modelo.precio = entidad.precio
        modelo.stock = entidad.stock
        modelo.imagen = entidad.imagen
        modelo.activo = entidad.activo
        modelo.categoria_id = entidad.categoria_id
        modelo.material = entidad.material
        modelo.tamano = entidad.tamano
        modelo.color = entidad.color
        modelo.specs = entidad.specs
        modelo.descuento = entidad.descuento
        modelo.badge = entidad.badge
        modelo.precio_original = entidad.precio_original
        modelo.rating = entidad.rating
        db.session.commit()
        return entidad

    def delete(self, entidad: Producto) -> None:
        modelo = db.session.get(self.model, entidad.id)
        if modelo is None:
            raise ValueError("Producto no encontrado en BD")
        try:
            db.session.delete(modelo)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError("No se puede eliminar el producto: tiene pedidos asociados")

    def guardar_imagen(self, producto_id: UUID, imagen: ImagenProducto) -> None:
        modelo = db.session.get(self.model, producto_id)
        if modelo:
            modelo.imagen_bytes = imagen.bytes
            modelo.imagen_content_type = imagen.content_type
            if not modelo.imagen:
                modelo.imagen = f"/api/productos/{producto_id}/imagen"
            db.session.commit()

    def _ejecutar(self, consulta: Any) -> list[Producto]:
        modelos = db.session.execute(consulta).scalars().all()
        return [_a_entidad(m) for m in modelos]


def _a_entidad(modelo: ProductoModel) -> Producto:
    return Producto(
        id=modelo.id,
        nombre=modelo.nombre,
        descripcion=modelo.descripcion,
        precio=modelo.precio,
        stock=modelo.stock,
        imagen=modelo.imagen,
        activo=modelo.activo,
        categoria_id=modelo.categoria_id,
        creado_en=modelo.creado_en,
        specs=modelo.specs,
        descuento=modelo.descuento,
        badge=modelo.badge,
        precio_original=modelo.precio_original,
        rating=modelo.rating,
        material=modelo.material,
        tamano=modelo.tamano,
        color=modelo.color,
    )


def _a_modelo(entidad: Producto) -> ProductoModel:
    return ProductoModel(
        id=entidad.id,
        nombre=entidad.nombre,
        descripcion=entidad.descripcion,
        precio=entidad.precio,
        stock=entidad.stock,
        imagen=entidad.imagen,
        activo=entidad.activo,
        categoria_id=entidad.categoria_id,
        creado_en=entidad.creado_en,
        material=entidad.material,
        tamano=entidad.tamano,
        color=entidad.color,
        specs=entidad.specs,
        descuento=entidad.descuento,
        badge=entidad.badge,
        precio_original=entidad.precio_original,
        rating=entidad.rating,
    )