import uuid

from app.infrastructure.database.connection import UuidRaw, db


class DetallePedidoModel(db.Model):
    __tablename__ = "detalle_pedidos"

    id = db.Column(UuidRaw, primary_key=True, default=uuid.uuid4)
    pedido_id = db.Column(UuidRaw, db.ForeignKey("pedidos.id"), nullable=False, index=True)
    producto_id = db.Column(UuidRaw, db.ForeignKey("productos.id"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Integer, nullable=False)