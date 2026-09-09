import uuid
from datetime import datetime

from app.infrastructure.database.connection import db


class UsuarioModel(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(30))
    rol = db.Column(db.String(20), nullable=False, default="cliente")
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)