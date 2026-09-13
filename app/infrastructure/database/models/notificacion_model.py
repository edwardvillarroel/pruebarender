import uuid
from datetime import datetime

from app.infrastructure.database.connection import UuidRaw, db


class NotificacionModel(db.Model):
    __tablename__ = "notificaciones"

    id = db.Column(UuidRaw, primary_key=True, default=uuid.uuid4)
    usuario_id = db.Column(UuidRaw, db.ForeignKey("usuarios.id"), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    canal = db.Column(db.String(20), nullable=False, default="email")
    asunto = db.Column(db.String(255))
    contenido = db.Column(db.Text)
    leida = db.Column(db.Boolean, nullable=False, default=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)