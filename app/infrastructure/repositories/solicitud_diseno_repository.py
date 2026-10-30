from __future__ import annotations

from typing import List
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

    def listar_todos(self) -> List[SolicitudDiseno]:
        modelos = self.model.query.order_by(self.model.creado_en.desc()).all()
        return [_a_entidad(m) for m in modelos]

    def listar_por_usuario(self, usuario_id: UUID) -> List[SolicitudDiseno]:
        modelos = (
            self.model.query.filter_by(usuario_id=usuario_id)
            .order_by(self.model.creado_en.desc())
            .all()
        )
        return [_a_entidad(m) for m in modelos]

    def obtener_por_id(self, solicitud_id: UUID) -> SolicitudDiseno | None:
        modelo = self.model.query.get(solicitud_id)
        if modelo is None:
            return None
        return _a_entidad(modelo)

    def actualizar(self, entidad: SolicitudDiseno) -> SolicitudDiseno:
        modelo = self.model.query.get(entidad.id)
        if modelo is None:
            raise ValueError("Solicitud no encontrada")
        modelo.nombre = entidad.nombre
        modelo.email = entidad.email
        modelo.telefono = entidad.telefono
        modelo.material = entidad.material
        modelo.descripcion = entidad.descripcion
        modelo.alto = entidad.alto
        modelo.ancho = entidad.ancho
        modelo.largo = entidad.largo
        modelo.unidad = entidad.unidad
        modelo.cantidad = entidad.cantidad
        modelo.uso = entidad.uso
        modelo.color = entidad.color
        modelo.imagen = entidad.imagen
        modelo.modelo_url = entidad.modelo_url
        modelo.precio = entidad.precio
        modelo.estado = entidad.estado.value if entidad.estado else EstadoSolicitud.PENDIENTE.value
        modelo.aviso_estado_en = getattr(entidad, "aviso_estado_en", None)
        modelo.aviso_estado_visto = bool(getattr(entidad, "aviso_estado_visto", False))
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
        material_sugerido_ia=getattr(modelo, "material_sugerido_ia", None),
        complejidad_ia=getattr(modelo, "complejidad_ia", None),
        gramos_estimados_ia=getattr(modelo, "gramos_estimados_ia", None),
        tiempo_estimado_horas_ia=getattr(modelo, "tiempo_estimado_horas_ia", None),
        precio_estimado_ia=getattr(modelo, "precio_estimado_ia", None),
        confianza_material_ia=getattr(modelo, "confianza_material_ia", None),
        confianza_complejidad_ia=getattr(modelo, "confianza_complejidad_ia", None),
        ia_calculado_en=getattr(modelo, "ia_calculado_en", None),
        ia_origen=getattr(modelo, "ia_origen", None),
        aviso_estado_en=getattr(modelo, "aviso_estado_en", None),
        aviso_estado_visto=bool(getattr(modelo, "aviso_estado_visto", False)),
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
        material_sugerido_ia=getattr(entidad, "material_sugerido_ia", None),
        complejidad_ia=getattr(entidad, "complejidad_ia", None),
        gramos_estimados_ia=getattr(entidad, "gramos_estimados_ia", None),
        tiempo_estimado_horas_ia=getattr(entidad, "tiempo_estimado_horas_ia", None),
        precio_estimado_ia=getattr(entidad, "precio_estimado_ia", None),
        confianza_material_ia=getattr(entidad, "confianza_material_ia", None),
        confianza_complejidad_ia=getattr(entidad, "confianza_complejidad_ia", None),
        ia_calculado_en=getattr(entidad, "ia_calculado_en", None),
        ia_origen=getattr(entidad, "ia_origen", None),
        aviso_estado_en=getattr(entidad, "aviso_estado_en", None),
        aviso_estado_visto=bool(getattr(entidad, "aviso_estado_visto", False)),
    )
