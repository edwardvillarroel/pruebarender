import uuid
from datetime import datetime

from app.infrastructure.database.connection import db, utcnow


class ResenaModel(db.Model):


    __tablename__ = "resenas"
    __table_args__ = (
        db.UniqueConstraint(
            "usuario_id",
            "pedido_id",
            "producto_id",
            name="uq_resenas_usuario_pedido_producto",
        ),
    )

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id = db.Column(db.Uuid, db.ForeignKey("usuarios.id"), nullable=False)
    pedido_id = db.Column(db.Uuid, db.ForeignKey("pedidos.id"), nullable=False)
    producto_id = db.Column(db.Uuid, db.ForeignKey("productos.id"), nullable=False)
    estrellas = db.Column(db.Numeric(3, 1), nullable=False)
    comentario = db.Column(db.Text)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    actualizado_en = db.Column(db.DateTime(timezone=True))
