"""Modelos de datos que consumen las plantillas de correo.

Viven acá para que el backend y el gateway compartan el mismo contrato sin que
`shared` dependa de `app`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence


@dataclass(frozen=True)
class Correo:
    """Contenido listo para enviar por el proveedor."""

    asunto: str
    html: str
    texto: str


@dataclass(frozen=True)
class ItemCorreo:
    nombre: str
    cantidad: int
    precio_unitario: int
    subtotal: int


@dataclass(frozen=True)
class DescuentoCorreo:
    etiqueta: str
    monto: int


@dataclass(frozen=True)
class PedidoCorreo:
    numero: str
    fecha: datetime | None
    email_cliente: str
    estado_pago: str
    items: Sequence[ItemCorreo]
    descuentos: Sequence[DescuentoCorreo]
    subtotal: int
    descuento_total: int
    costo_envio: int
    total: int
    tipo_entrega: str
    direccion: str | None
    notas: str | None


@dataclass(frozen=True)
class CotizacionCorreo:
    numero: str
    fecha: datetime | None
    nombre: str
    email: str
    telefono: str | None
    material: str
    alto: float | None
    ancho: float | None
    largo: float | None
    unidad: str
    cantidad: int
    uso: str | None
    color: str | None
    descripcion: str
    precio: int | None
    estado: str
    material_sugerido_ia: str | None = None
    complejidad_ia: str | None = None
    gramos_estimados_ia: float | None = None
    tiempo_estimado_horas_ia: float | None = None
    precio_estimado_ia: int | None = None


@dataclass(frozen=True)
class ProductoCorreo:
    nombre: str
    stock: int
    stock_minimo: int
