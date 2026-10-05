import uuid
from datetime import datetime

from app.infrastructure.database.connection import db, utcnow


class PedidoModel(db.Model):
    __tablename__ = "pedidos"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id = db.Column(db.Uuid, db.ForeignKey("usuarios.id"), nullable=False)
    estado = db.Column(db.String(30), nullable=False, default="pendiente")
    total = db.Column(db.Integer, nullable=False, default=0)
    direccion_envio = db.Column(db.Text)
    entrega = db.Column(db.String(20), default="retiro")
    codigo_seguimiento = db.Column(db.String(50))
    estado_seguimiento = db.Column(db.String(100))
    seguimiento_actualizado_en = db.Column(db.DateTime(timezone=True))
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    detalles = db.relationship(
        "DetallePedidoModel",
        back_populates="pedido",
        cascade="all, delete-orphan",
    )
