"""Repositorio de productos (SQLAlchemy) con mapeo ORM -> dominio.

Implementa la interfaz `ProductoRepository` de la capa de dominio. Los objetos
que cruzan la frontera de infraestructura son siempre entidades `Producto`, no
modelos ORM.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update

from app.domain.entities.producto import (
    ColorProducto,
    FotoColorCatalogo,
    ImagenProducto,
    Producto,
)
from app.domain.interfaces.repositories import (
    ProductoRepository as ProductoRepositoryInterface,
)
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.producto_color_model import ProductoColorModel
from app.infrastructure.database.models.producto_model import ProductoModel

RUTA_IMAGEN_COLOR = "/api/productos/colores/{color_id}/imagen"
RUTA_THUMB_COLOR = "/api/productos/colores/{color_id}/thumb"
RUTA_IMAGEN_PRODUCTO = "/api/productos/{producto_id}/imagen"
RUTA_THUMB_PRODUCTO = "/api/productos/{producto_id}/thumb"


class ProductoRepository(ProductoRepositoryInterface):
    model = ProductoModel

    def get_by_id(self, entity_id: UUID) -> Producto | None:
        fila = db.session.execute(
            select(
                self.model,
                self.model.imagen_thumb_bytes.isnot(None).label("tiene_thumb"),
                self.model.imagen_bytes.isnot(None).label("tiene_imagen"),
            ).where(self.model.id == entity_id)
        ).first()
        if fila is None:
            return None
        return _a_entidad(fila[0], tiene_thumb=fila[1], tiene_imagen=fila[2])

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
        # `imagen_bytes` e `imagen_thumb_bytes` son deferred: se pregunta solo por
        # su existencia con `isnot(None)` en el mismo SELECT. Leer el atributo
        # dentro del mapeo dispararia una consulta extra por producto (N+1) y el
        # listado volveria a ir lento, que es justo lo que se vino a arreglar.
        filas = db.session.execute(
            select(
                self.model,
                self.model.imagen_thumb_bytes.isnot(None).label("tiene_thumb"),
                self.model.imagen_bytes.isnot(None).label("tiene_imagen"),
            )
            .where(self.model.activo == True)  # noqa: E712 - Oracle: activo = 1
            .order_by(self.model.nombre)
        ).all()
        return [
            _a_entidad(f[0], tiene_thumb=f[1], tiene_imagen=f[2]) for f in filas
        ]

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
        modelo.activo = False
        db.session.commit()

    def guardar_imagen(self, producto_id: UUID, imagen: ImagenProducto) -> None:
        modelo = db.session.get(self.model, producto_id)
        if modelo:
            modelo.imagen_bytes = imagen.bytes
            modelo.imagen_content_type = imagen.content_type
            if not modelo.imagen:
                modelo.imagen = f"/api/productos/{producto_id}/imagen"
            # La foto cambio: el thumbnail cacheado ya no corresponde.
            modelo.imagen_thumb_bytes = None
            modelo.imagen_thumb_content_type = None
            db.session.commit()

    def list_colores(self, producto_id: UUID) -> list[ColorProducto]:
        filas = db.session.execute(
            select(
                ProductoColorModel.id,
                ProductoColorModel.producto_id,
                ProductoColorModel.nombre,
                ProductoColorModel.orden,
                ProductoColorModel.imagen_bytes.isnot(None).label("tiene_imagen"),
                ProductoColorModel.imagen_thumb_bytes.isnot(None).label("tiene_thumb"),
            )
            .where(ProductoColorModel.producto_id == producto_id)
            .order_by(ProductoColorModel.orden, ProductoColorModel.nombre)
        ).all()
        return [
            ColorProducto(
                id=f.id,
                producto_id=f.producto_id,
                nombre=f.nombre,
                orden=f.orden or 0,
                imagen_url=_ruta_imagen_color(f.id) if f.tiene_imagen else None,
                imagen_thumb_url=(
                    _ruta_thumb_color(f.id) if f.tiene_imagen and f.tiene_thumb else None
                ),
            )
            for f in filas
        ]

    def primera_imagen_color_por_producto(
        self, producto_ids: list[UUID]
    ) -> dict[UUID, FotoColorCatalogo]:
        """Foto del primer color de cada producto, en una sola consulta.

        Se resuelve con el menor `orden` de cada producto (el primero que se
        agrego) usando `min() GROUP BY`, y no con un loop que consultaria una
        vez por producto: el listado del catalogo puede tener 20+ productos.
        """
        if not producto_ids:
            return {}
        filas = db.session.execute(
            select(
                ProductoColorModel.producto_id,
                func.min(ProductoColorModel.orden).label("primer_orden"),
            )
            .where(
                ProductoColorModel.producto_id.in_(producto_ids),
                ProductoColorModel.imagen_bytes.isnot(None),
            )
            .group_by(ProductoColorModel.producto_id)
        ).all()

        if not filas:
            return {}

        # Segundo paso: traer el color que quedo primero en cada grupo. El
        # filtro `imagen_bytes.isnot(None)` es indispensable: sin el, un color
        # sin foto con `orden=0` le ganaria a uno con foto en `orden=1` y la
        # tarjeta apuntaria a una URL que devuelve 404.
        pedidos = {f.producto_id for f in filas}
        candidatos = db.session.execute(
            select(
                ProductoColorModel.producto_id,
                ProductoColorModel.id,
                ProductoColorModel.orden,
                ProductoColorModel.imagen_thumb_bytes.isnot(None).label("tiene_thumb"),
            ).where(
                ProductoColorModel.producto_id.in_(list(pedidos)),
                ProductoColorModel.imagen_bytes.isnot(None),
            )
        ).all()

        mejor: dict[UUID, tuple[int, UUID, bool]] = {}
        for producto_id, color_id, orden, tiene_thumb in candidatos:
            orden = orden or 0
            actual = mejor.get(producto_id)
            if actual is None or orden < actual[0]:
                mejor[producto_id] = (orden, color_id, bool(tiene_thumb))

        return {
            producto_id: FotoColorCatalogo(
                imagen_url=_ruta_imagen_color(color_id),
                imagen_thumb_url=(
                    _ruta_thumb_color(color_id) if tiene_thumb else None
                ),
            )
            for producto_id, (_, color_id, tiene_thumb) in mejor.items()
        }

    def get_color_by_id(self, color_id: UUID) -> ColorProducto | None:
        fila = db.session.execute(
            select(
                ProductoColorModel.id,
                ProductoColorModel.producto_id,
                ProductoColorModel.nombre,
                ProductoColorModel.orden,
                ProductoColorModel.imagen_bytes.isnot(None).label("tiene_imagen"),
                ProductoColorModel.imagen_thumb_bytes.isnot(None).label("tiene_thumb"),
            ).where(ProductoColorModel.id == color_id)
        ).first()
        if fila is None:
            return None
        return ColorProducto(
            id=fila.id,
            producto_id=fila.producto_id,
            nombre=fila.nombre,
            orden=fila.orden or 0,
            imagen_url=_ruta_imagen_color(fila.id) if fila.tiene_imagen else None,
            imagen_thumb_url=(
                _ruta_thumb_color(fila.id)
                if fila.tiene_imagen and fila.tiene_thumb
                else None
            ),
        )

    def get_color_imagen_by_id(self, color_id: UUID) -> ImagenProducto | None:
        fila = db.session.execute(
            select(
                ProductoColorModel.imagen_bytes,
                ProductoColorModel.imagen_content_type,
            ).where(ProductoColorModel.id == color_id)
        ).first()
        if fila is None or fila.imagen_bytes is None:
            return None
        return ImagenProducto(
            bytes=fila.imagen_bytes, content_type=fila.imagen_content_type
        )

    def get_thumb_by_id(self, producto_id: UUID) -> ImagenProducto | None:
        fila = db.session.execute(
            select(
                ProductoModel.imagen_thumb_bytes,
                ProductoModel.imagen_thumb_content_type,
            ).where(ProductoModel.id == producto_id)
        ).first()
        if fila is None or fila.imagen_thumb_bytes is None:
            return None
        return ImagenProducto(
            bytes=fila.imagen_thumb_bytes,
            content_type=fila.imagen_thumb_content_type,
        )

    def guardar_thumb(self, producto_id: UUID, thumb: ImagenProducto) -> None:
        modelo = db.session.get(self.model, producto_id)
        if modelo is None:
            raise ValueError("Producto no encontrado en BD")
        modelo.imagen_thumb_bytes = thumb.bytes
        modelo.imagen_thumb_content_type = thumb.content_type
        db.session.commit()

    def get_color_thumb_by_id(self, color_id: UUID) -> ImagenProducto | None:
        fila = db.session.execute(
            select(
                ProductoColorModel.imagen_thumb_bytes,
                ProductoColorModel.imagen_thumb_content_type,
            ).where(ProductoColorModel.id == color_id)
        ).first()
        if fila is None or fila.imagen_thumb_bytes is None:
            return None
        return ImagenProducto(
            bytes=fila.imagen_thumb_bytes,
            content_type=fila.imagen_thumb_content_type,
        )

    def guardar_color_thumb(self, color_id: UUID, thumb: ImagenProducto) -> None:
        db.session.execute(
            update(ProductoColorModel)
            .where(ProductoColorModel.id == color_id)
            .values(
                imagen_thumb_bytes=thumb.bytes,
                imagen_thumb_content_type=thumb.content_type,
            )
        )
        db.session.commit()

    def guardar_color(
        self, producto_id: UUID, nombre: str, imagen: ImagenProducto
    ) -> ColorProducto:
        nombre = (nombre or "").strip()
        if not nombre:
            raise ValueError("El nombre del color es obligatorio")

        modelo = db.session.execute(
            select(ProductoColorModel).where(
                ProductoColorModel.producto_id == producto_id,
                ProductoColorModel.nombre == nombre,
            )
        ).scalar_one_or_none()

        if modelo is None:
            siguiente = db.session.execute(
                select(func.coalesce(func.max(ProductoColorModel.orden), -1) + 1).where(
                    ProductoColorModel.producto_id == producto_id
                )
            ).scalar_one()
            modelo = ProductoColorModel(
                producto_id=producto_id, nombre=nombre, orden=siguiente
            )
            db.session.add(modelo)

        modelo.imagen_bytes = imagen.bytes
        modelo.imagen_content_type = imagen.content_type
        # La foto cambio: el thumbnail viejo ya no corresponde y se regenera
        # en el proximo request. Sin esto la tarjeta mostraria la foto anterior.
        modelo.imagen_thumb_bytes = None
        modelo.imagen_thumb_content_type = None
        db.session.commit()

        return ColorProducto(
            id=modelo.id,
            producto_id=producto_id,
            nombre=modelo.nombre,
            orden=modelo.orden or 0,
            imagen_url=_ruta_imagen_color(modelo.id),
        )

    def eliminar_color(self, color_id: UUID) -> None:
        modelo = db.session.get(ProductoColorModel, color_id)
        if modelo is None:
            raise ValueError("Color no encontrado")
        db.session.delete(modelo)
        db.session.commit()

    def _ejecutar(self, consulta: Any) -> list[Producto]:
        modelos = db.session.execute(consulta).scalars().all()
        return [_a_entidad(m) for m in modelos]


def _ruta_imagen_color(color_id: UUID) -> str:
    return RUTA_IMAGEN_COLOR.format(color_id=color_id)


def _ruta_thumb_color(color_id: UUID) -> str:
    return RUTA_THUMB_COLOR.format(color_id=color_id)


def _a_entidad(
    modelo: ProductoModel,
    tiene_thumb: bool = False,
    tiene_imagen: bool | None = None,
) -> Producto:
    # La foto real vive en `imagen_bytes`; `modelo.imagen` es solo la URL y se
    # escribe una vez al subir la foto, sin volver a validarse nunca. Cuando el
    # BLOB no esta pero la URL quedo guardada, la tarjeta pedia una imagen que
    # responde 404 y el producto se excluia de `listar_con_foto_de_color`, de
    # modo que las fotos de color nunca llegaban a la tarjeta. El BLOB manda:
    # sin BLOB no hay foto.
    # `tiene_imagen=None` significa "esta consulta no lo consulto": se respeta el
    # valor previo para no cambiar el comportamiento de los otros callers.
    if tiene_imagen is None:
        imagen = modelo.imagen
    else:
        imagen = (
            RUTA_IMAGEN_PRODUCTO.format(producto_id=modelo.id) if tiene_imagen else None
        )
    return Producto(
        id=modelo.id,
        nombre=modelo.nombre,
        descripcion=modelo.descripcion,
        precio=modelo.precio,
        stock=modelo.stock,
        imagen=imagen,
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
        imagen_thumb=(
            RUTA_THUMB_PRODUCTO.format(producto_id=modelo.id) if tiene_thumb else None
        ),
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
