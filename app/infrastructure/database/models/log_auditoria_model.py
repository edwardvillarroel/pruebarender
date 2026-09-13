import uuid
from datetime import datetime

from app.infrastructure.database.connection import UuidRaw, db


class LogAuditoriaModel(db.Model):
    __tablename__ = "logs_auditoria"

    id = db.Column(UuidRaw, primary_key=True, default=uuid.uuid4)
    usuario_id = db.Column(UuidRaw, db.ForeignKey("usuarios.id"))
    accion = db.Column(db.String(100), nullable=False)
    entidad_tipo = db.Column(db.String(50), nullable=False)
    entidad_id = db.Column(db.String(50))
    detalle = db.Column(db.Text)
    ip = db.Column(db.String(45))
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)