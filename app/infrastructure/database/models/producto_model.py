import json
import uuid
from datetime import datetime

from sqlalchemy import LargeBinary
from sqlalchemy.orm import deferred

from app.infrastructure.database.connection import db, utcnow


class ProductoModel(db.Model):
    __tablename__ = "productos"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    categoria_id = db.Column(db.Uuid, db.ForeignKey("categorias.id"), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    imagen = db.Column(db.String(500))
    imagen_url = db.Column(db.Text)
    imagen_bytes = deferred(db.Column(LargeBinary))
    imagen_content_type = db.Column(db.String(50))
    imagen_thumb_bytes = deferred(db.Column(LargeBinary))
    imagen_thumb_content_type = db.Column(db.String(50))
    activo = db.Column(db.Boolean, nullable=False, default=True)
    nuevo_lanzamiento = db.Column(db.Boolean, nullable=False, default=False)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    specs_raw = db.Column("specs", db.Text)
    descuento = db.Column(db.Integer)
    badge = db.Column(db.String(50))
    precio_original = db.Column(db.Integer)
    rating = db.Column(db.Numeric(3, 1))
    resenas_count = db.Column(db.Integer, nullable=False, default=0)
    material = db.Column(db.String(100))
    tamano = db.Column(db.String(100))
    color = db.Column(db.String(100))
    stock_minimo = db.Column(db.Integer)
    aviso_stock_enviado = db.Column(db.Boolean, nullable=False, default=False)
    aviso_stock_notificado_en = db.Column(db.DateTime(timezone=True))

    @property
    def specs(self) -> list[str] | None:
        if self.specs_raw is None:
            return None
        return json.loads(self.specs_raw)

    @specs.setter
    def specs(self, value: list[str] | None) -> None:
        self.specs_raw = json.dumps(value) if value is not None else None
