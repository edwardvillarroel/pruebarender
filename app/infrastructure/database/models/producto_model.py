import uuid
from datetime import datetime

from app.infrastructure.database.connection import db


class ProductoModel(db.Model):
    __tablename__ = "productos"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    categoria_id = db.Column(db.Uuid, db.ForeignKey("categorias.id"), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    imagen = db.Column(db.String(500))
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)