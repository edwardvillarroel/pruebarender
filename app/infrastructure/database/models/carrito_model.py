"""Modelos ORM del carrito de compras (tablas `carrito` / `carrito_items`).

Las claves son UUIDs en RAW(16) (`UuidRaw`) y las fechas usan
TIMESTAMP WITH TIME ZONE igual que el esquema en Oracle.
"""

import uuid
from datetime import datetime

from app.infrastructure.database.connection import UuidRaw, db


class CarritoModel(db.Model):
    __tablename__ = "carrito"

    id = db.Column(UuidRaw, primary_key=True, default=uuid.uuid4)
    usuario_id = db.Column(UuidRaw, unique=True, nullable=False)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    actualizado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    items = db.relationship(
        "CarritoItemModel",
        back_populates="carrito",
        cascade="all, delete-orphan",
        order_by="CarritoItemModel.agregado_en",
    )


class CarritoItemModel(db.Model):
    __tablename__ = "carrito_items"

    id = db.Column(UuidRaw, primary_key=True, default=uuid.uuid4)
    carrito_id = db.Column(UuidRaw, db.ForeignKey("carrito.id"), nullable=False)
    producto_id = db.Column(UuidRaw, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    agregado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    carrito = db.relationship("CarritoModel", back_populates="items")