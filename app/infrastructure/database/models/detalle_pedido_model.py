import uuid

from app.infrastructure.database.connection import db


class DetallePedidoModel(db.Model):
    __tablename__ = "detalle_pedidos"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    pedido_id = db.Column(db.Uuid, db.ForeignKey("pedidos.id"), nullable=False, index=True)
    producto_id = db.Column(db.Uuid, db.ForeignKey("productos.id"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Integer, nullable=False)