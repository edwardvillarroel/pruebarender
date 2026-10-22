import uuid
from datetime import datetime

from app.infrastructure.database.connection import db, utcnow


class CuponModel(db.Model):
    __tablename__ = "cupones"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    codigo = db.Column(db.String(30), unique=True, nullable=False, index=True)
    tipo = db.Column(db.String(10), nullable=False, default="porcentaje")
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    uso_unico = db.Column(db.Boolean, nullable=False, default=False)
    usado = db.Column(db.Boolean, nullable=False, default=False)
    usado_por = db.Column(db.Uuid, db.ForeignKey("usuarios.id"))
    usado_en = db.Column(db.DateTime(timezone=True))
    creado_por = db.Column(db.Uuid, db.ForeignKey("usuarios.id"))
    descripcion = db.Column(db.String(255))
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
