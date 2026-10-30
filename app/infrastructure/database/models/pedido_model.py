import uuid
from datetime import datetime

from app.infrastructure.database.connection import db, utcnow


class PedidoModel(db.Model):
    __tablename__ = "pedidos"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id = db.Column(db.Uuid, db.ForeignKey("usuarios.id"), nullable=False)
    cotizacion_id = db.Column(
        db.Uuid,
        db.ForeignKey("solicitudes_diseno.id"),
        nullable=True,
        unique=True,
    )
    estado = db.Column(db.String(30), nullable=False, default="pendiente")
    total = db.Column(db.Integer, nullable=False, default=0)
    subtotal = db.Column(db.Integer)
    descuento_productos = db.Column(db.Integer, nullable=False, default=0)
    descuento_cupon = db.Column(db.Integer, nullable=False, default=0)
    cupon_codigo = db.Column(db.String(30))
    direccion_envio = db.Column(db.Text)
    entrega = db.Column(db.String(20), default="retiro")
    tipo_documento = db.Column(db.String(20))
    codigo_seguimiento = db.Column(db.String(50))
    transportista = db.Column(db.String(30))
    estado_seguimiento = db.Column(db.String(100))
    seguimiento_actualizado_en = db.Column(db.DateTime(timezone=True))
    aviso_cancelacion_en = db.Column(db.DateTime(timezone=True))
    aviso_cancelacion_visto = db.Column(db.Boolean, nullable=False, default=False)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    detalles = db.relationship(
        "DetallePedidoModel",
        back_populates="pedido",
        cascade="all, delete-orphan",
    )
