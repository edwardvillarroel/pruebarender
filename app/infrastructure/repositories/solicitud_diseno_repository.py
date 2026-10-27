from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.domain.entities.solicitud_diseno import EstadoSolicitud, SolicitudDiseno
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.solicitud_diseno_model import SolicitudDisenoModel


class SolicitudDisenoRepository:
    model = SolicitudDisenoModel

    def crear(self, entidad: SolicitudDiseno) -> SolicitudDiseno:
        modelo = _a_modelo(entidad)
        db.session.add(modelo)
        db.session.commit()
        return _a_entidad(modelo)


def _a_entidad(modelo: SolicitudDisenoModel) -> SolicitudDiseno:
    return SolicitudDiseno(
        id=modelo.id,
        usuario_id=modelo.usuario_id,
        nombre=modelo.nombre,
        email=modelo.email,
        telefono=modelo.telefono,
        material=modelo.material,
        descripcion=modelo.descripcion,
        alto=modelo.alto,
        ancho=modelo.ancho,
        largo=modelo.largo,
        unidad=modelo.unidad or "cm",
        cantidad=modelo.cantidad or 1,
        uso=modelo.uso,
        color=modelo.color,
        imagen=modelo.imagen,
        modelo_url=modelo.modelo_url,
        precio=modelo.precio,
        estado=EstadoSolicitud(modelo.estado) if modelo.estado else EstadoSolicitud.PENDIENTE,
        creado_en=modelo.creado_en,
    )


def _a_modelo(entidad: SolicitudDiseno) -> SolicitudDisenoModel:
    return SolicitudDisenoModel(
        id=entidad.id,
        usuario_id=entidad.usuario_id,
        nombre=entidad.nombre,
        email=entidad.email,
        telefono=entidad.telefono,
        material=entidad.material,
        descripcion=entidad.descripcion,
        alto=entidad.alto,
        ancho=entidad.ancho,
        largo=entidad.largo,
        unidad=entidad.unidad or "cm",
        cantidad=entidad.cantidad or 1,
        uso=entidad.uso,
        color=entidad.color,
        imagen=entidad.imagen,
        modelo_url=entidad.modelo_url,
        precio=entidad.precio,
        estado=entidad.estado.value if entidad.estado else EstadoSolicitud.PENDIENTE.value,
        creado_en=entidad.creado_en,
    )
