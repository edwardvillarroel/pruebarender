import uuid
from datetime import datetime

from app.infrastructure.database.connection import db, utcnow


class DocumentoTributarioModel(db.Model):


    __tablename__ = "documentos_tributarios"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    pedido_id = db.Column(
        db.Uuid, db.ForeignKey("pedidos.id", ondelete="CASCADE"), unique=True
    )
    tipo_dte = db.Column(db.SmallInteger, nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="pendiente")
    clave_idempotencia = db.Column(db.String(120), nullable=False, unique=True)
    folio = db.Column(db.Integer)
    token = db.Column(db.String(120))
    rut_emisor = db.Column(db.String(20), nullable=False)
    rut_receptor = db.Column(db.String(20), nullable=False)
    razon_social_receptor = db.Column(db.String(200))
    giro_receptor = db.Column(db.String(200))
    direccion_receptor = db.Column(db.String(300))
    comuna_receptor = db.Column(db.String(120))
    monto_neto = db.Column(db.Integer, nullable=False, default=0)
    iva = db.Column(db.Integer, nullable=False, default=0)
    monto_total = db.Column(db.Integer, nullable=False, default=0)
    fecha_emision = db.Column(db.Date)
    error = db.Column(db.Text)
    pdf = db.Column(db.LargeBinary)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
