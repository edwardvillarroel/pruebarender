import uuid

from app.infrastructure.database.connection import db


class CategoriaModel(db.Model):
    __tablename__ = "categorias"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.Text)