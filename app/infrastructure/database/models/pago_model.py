import uuid
from datetime import datetime

from app.infrastructure.database.connection import db


class PagoModel(db.Model):
    __tablename__ = "pagos"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    pedido_id = db.Column(db.Uuid, db.ForeignKey("pedidos.id"), nullable=False)
    monto = db.Column(db.Integer, nullable=False)
    proveedor = db.Column(db.String(50), nullable=False)
    token = db.Column(db.String(255))
    estado = db.Column(db.String(30), nullable=False, default="pendiente")
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)