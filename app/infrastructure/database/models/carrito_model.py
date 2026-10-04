"""Modelos ORM del carrito de compras (tablas `carrito` / `carrito_items`).

Las claves son UUIDs en RAW(16) (`db.Uuid`) y las fechas usan
TIMESTAMP WITH TIME ZONE igual que el esquema en Oracle.
"""

import uuid
from datetime import datetime

from app.infrastructure.database.connection import db, utcnow


class CarritoModel(db.Model):
    __tablename__ = "carrito"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id = db.Column(db.Uuid, unique=True, nullable=False)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    actualizado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    items = db.relationship(
        "CarritoItemModel",
        back_populates="carrito",
        cascade="all, delete-orphan",
        order_by="CarritoItemModel.agregado_en",
    )


class CarritoItemModel(db.Model):
    __tablename__ = "carrito_items"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    carrito_id = db.Column(db.Uuid, db.ForeignKey("carrito.id"), nullable=False)
    producto_id = db.Column(db.Uuid, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String(50))
    agregado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    carrito = db.relationship("CarritoModel", back_populates="items")
