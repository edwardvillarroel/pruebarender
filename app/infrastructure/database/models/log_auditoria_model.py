import uuid
from datetime import datetime

from app.infrastructure.database.connection import db, utcnow


class LogAuditoriaModel(db.Model):
    __tablename__ = "logs_auditoria"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id = db.Column(db.Uuid, db.ForeignKey("usuarios.id"))
    accion = db.Column(db.String(100), nullable=False)
    entidad_tipo = db.Column(db.String(50), nullable=False)
    entidad_id = db.Column(db.String(50))
    detalle = db.Column(db.Text)
    ip = db.Column(db.String(45))
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
