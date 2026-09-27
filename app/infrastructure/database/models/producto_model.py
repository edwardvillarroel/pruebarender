import json
import uuid
from datetime import datetime

from sqlalchemy import LargeBinary
from sqlalchemy.orm import deferred

from app.infrastructure.database.connection import UuidRaw, db


class ProductoModel(db.Model):
    __tablename__ = "productos"

    id = db.Column(UuidRaw, primary_key=True, default=uuid.uuid4)
    categoria_id = db.Column(UuidRaw, db.ForeignKey("categorias.id"), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    imagen = db.Column(db.String(500))
    imagen_bytes = deferred(db.Column(LargeBinary))
    imagen_content_type = db.Column(db.String(50))
    # Thumbnail generado perezosamente desde `imagen_bytes` para el catalogo.
    # `imagen_bytes` sigue siendo la foto en resolucion completa.
    imagen_thumb_bytes = deferred(db.Column(LargeBinary))
    imagen_thumb_content_type = db.Column(db.String(50))
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    specs_raw = db.Column("specs", db.Text)
    descuento = db.Column(db.Integer)
    badge = db.Column(db.String(50))
    precio_original = db.Column(db.Integer)
    rating = db.Column(db.Integer)
    material = db.Column(db.String(100))
    tamano = db.Column(db.String(100))
    color = db.Column(db.String(100))

    @property
    def specs(self) -> list[str] | None:
        """Lee specs como lista desde el Text serializado en JSON."""
        if self.specs_raw is None:
            return None
        return json.loads(self.specs_raw)

    @specs.setter
    def specs(self, value: list[str] | None) -> None:
        """Serializa la lista a JSON string para almacenar en Text."""
        self.specs_raw = json.dumps(value) if value is not None else None
