import uuid

from app.infrastructure.database.connection import db, utcnow


class SolicitudDisenoModel(db.Model):
    __tablename__ = "solicitudes_diseno"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id = db.Column(db.Uuid, db.ForeignKey("usuarios.id"), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    telefono = db.Column(db.String(30))
    material = db.Column(db.String(30), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(30), nullable=False, default="pendiente")
    imagen = db.Column(db.String(500))
    modelo_url = db.Column(db.String(500))
    precio = db.Column(db.Numeric(10, 2))
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    alto = db.Column(db.Numeric(8, 2))
    ancho = db.Column(db.Numeric(8, 2))
    largo = db.Column(db.Numeric(8, 2))
    unidad = db.Column(db.String(10), default="cm")
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    uso = db.Column(db.String(30))
    color = db.Column(db.String(60))
