import uuid
from datetime import datetime

from app.infrastructure.database.connection import UuidRaw, db


class PedidoModel(db.Model):
    __tablename__ = "pedidos"

    id = db.Column(UuidRaw, primary_key=True, default=uuid.uuid4)
    usuario_id = db.Column(UuidRaw, db.ForeignKey("usuarios.id"), nullable=False)
    estado = db.Column(db.String(30), nullable=False, default="pendiente")
    total = db.Column(db.Integer, nullable=False, default=0)
    direccion_envio = db.Column(db.Text)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)