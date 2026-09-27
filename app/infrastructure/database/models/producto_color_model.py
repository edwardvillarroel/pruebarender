"""Modelo ORM de los colores de un producto (tabla `producto_colores`).

Cada fila es una variante de color con su propia imagen. Los bytes viven en la
tabla (BLOB) y no en `productos`, para poder servir cada foto por separado.
"""

import uuid
from datetime import datetime

from sqlalchemy import LargeBinary
from sqlalchemy.orm import deferred

from app.infrastructure.database.connection import UuidRaw, db


class ProductoColorModel(db.Model):
    __tablename__ = "producto_colores"

    id = db.Column(UuidRaw, primary_key=True, default=uuid.uuid4)
    producto_id = db.Column(
        UuidRaw, db.ForeignKey("productos.id"), nullable=False, index=True
    )
    nombre = db.Column(db.String(50), nullable=False)
    imagen_bytes = deferred(db.Column(LargeBinary))
    imagen_content_type = db.Column(db.String(50))
    # Thumbnail generado perezosamente desde `imagen_bytes`; la foto original se
    # conserva intacta para la vista de detalle.
    imagen_thumb_bytes = deferred(db.Column(LargeBinary))
    imagen_thumb_content_type = db.Column(db.String(50))
    orden = db.Column(db.Integer, nullable=False, default=0)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
