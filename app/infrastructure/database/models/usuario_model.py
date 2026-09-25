import uuid
from datetime import datetime

from app.infrastructure.database.connection import UuidRaw, db


class UsuarioModel(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(UuidRaw, primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(30))
    rol = db.Column(db.String(20), nullable=False, default="cliente")
    activo = db.Column(db.Boolean, nullable=False, default=True)
    auth_provider = db.Column(db.String(20), nullable=False, default="local")
    google_sub = db.Column(db.String(255))
    mfa_secret = db.Column(db.String(64))
    mfa_activo = db.Column(db.Boolean, nullable=False, default=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)