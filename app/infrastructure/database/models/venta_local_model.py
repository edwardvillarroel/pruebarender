"""Modelos ORM de la venta local.

Tablas `sesiones_venta`, `ventas_local` y `venta_local_items`. Las claves son
UUIDs en RAW(16) (`UuidRaw`) y las fechas usan `db.DateTime` como el resto de
los modelos de infraestructura.
"""

import uuid
from datetime import datetime

from app.infrastructure.database.connection import UuidRaw, db


class SesionVentaModel(db.Model):
    __tablename__ = "sesiones_venta"

    id = db.Column(UuidRaw, primary_key=True, default=uuid.uuid4)
    lugar = db.Column(db.String(150), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    estado = db.Column(db.String(20), nullable=False)
    usuario_id = db.Column(UuidRaw, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    cerrada_en = db.Column(db.DateTime, nullable=True)

    ventas = db.relationship(
        "VentaLocalModel",
        back_populates="sesion",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class VentaLocalModel(db.Model):
    __tablename__ = "ventas_local"

    id = db.Column(UuidRaw, primary_key=True, default=uuid.uuid4)
    sesion_id = db.Column(UuidRaw, db.ForeignKey("sesiones_venta.id"), nullable=False, index=True)
    medio_pago = db.Column(db.String(20), nullable=False)
    total = db.Column(db.Integer, nullable=False, default=0)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    sesion = db.relationship("SesionVentaModel", back_populates="ventas")
    items = db.relationship(
        "VentaLocalItemModel",
        back_populates="venta",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class VentaLocalItemModel(db.Model):
    __tablename__ = "venta_local_items"

    id = db.Column(UuidRaw, primary_key=True, default=uuid.uuid4)
    venta_id = db.Column(UuidRaw, db.ForeignKey("ventas_local.id"), nullable=False, index=True)
    producto_id = db.Column(UuidRaw, db.ForeignKey("productos.id"), nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Integer, nullable=False)

    venta = db.relationship("VentaLocalModel", back_populates="items")