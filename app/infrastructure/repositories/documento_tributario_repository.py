from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.domain.entities.documento_tributario import DocumentoTributario
from app.domain.enums import EstadoDocumentoTributario, TipoDocumentoTributario
from app.domain.interfaces.repositories import (
    DocumentoTributarioRepository as DocumentoTributarioRepositoryInterface,
)
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.documento_tributario_model import (
    DocumentoTributarioModel,
)


class DocumentoTributarioRepository(DocumentoTributarioRepositoryInterface):
    model = DocumentoTributarioModel

    def get_by_id(self, entity_id: UUID) -> DocumentoTributario | None:
        modelo = db.session.get(self.model, entity_id)
        return _a_entidad(modelo) if modelo else None

    def list(self, *filters: Any) -> list[DocumentoTributario]:
        consulta = db.session.query(self.model)
        if filters:
            consulta = consulta.filter(*filters)
        return [_a_entidad(m) for m in consulta.all()]

    def get_by_pedido(self, pedido_id: UUID) -> DocumentoTributario | None:
        modelo = db.session.execute(
            select(self.model).where(self.model.pedido_id == pedido_id)
        ).scalar_one_or_none()
        return _a_entidad(modelo) if modelo else None

    def get_by_clave_idempotencia(self, clave: str) -> DocumentoTributario | None:
        modelo = db.session.execute(
            select(self.model).where(self.model.clave_idempotencia == clave)
        ).scalar_one_or_none()
        return _a_entidad(modelo) if modelo else None

    def add(self, entidad: DocumentoTributario) -> DocumentoTributario:
        db.session.add(_a_modelo(entidad))
        db.session.commit()
        return entidad

    def update(self, entidad: DocumentoTributario) -> DocumentoTributario:
        modelo = db.session.get(self.model, entidad.id)
        if modelo is None:
            raise ValueError("Documento tributario no encontrado en BD")
        _copiar_a_modelo(entidad, modelo)
        db.session.commit()
        return entidad

    def delete(self, entidad: DocumentoTributario) -> None:
        modelo = db.session.get(self.model, entidad.id)
        if modelo is None:
            raise ValueError("Documento tributario no encontrado en BD")
        db.session.delete(modelo)
        db.session.commit()


def _a_entidad(modelo: DocumentoTributarioModel) -> DocumentoTributario:
    return DocumentoTributario(
        id=modelo.id,
        pedido_id=modelo.pedido_id,
        tipo=_a_tipo(modelo.tipo_dte),
        estado=EstadoDocumentoTributario(modelo.estado),
        clave_idempotencia=modelo.clave_idempotencia,
        folio=modelo.folio,
        token=modelo.token,
        rut_emisor=modelo.rut_emisor,
        rut_receptor=modelo.rut_receptor,
        razon_social_receptor=modelo.razon_social_receptor,
        giro_receptor=modelo.giro_receptor,
        direccion_receptor=modelo.direccion_receptor,
        comuna_receptor=modelo.comuna_receptor,
        monto_neto=modelo.monto_neto,
        iva=modelo.iva,
        monto_total=modelo.monto_total,
        fecha_emision=modelo.fecha_emision,
        error=modelo.error,
        pdf=modelo.pdf,
        creado_en=modelo.creado_en,
    )


def _a_modelo(entidad: DocumentoTributario) -> DocumentoTributarioModel:
    modelo = DocumentoTributarioModel(id=entidad.id)
    _copiar_a_modelo(entidad, modelo)
    return modelo


def _copiar_a_modelo(
    entidad: DocumentoTributario, modelo: DocumentoTributarioModel
) -> None:
    modelo.pedido_id = entidad.pedido_id
    modelo.tipo_dte = entidad.tipo.codigo_dte
    modelo.estado = entidad.estado.value
    modelo.clave_idempotencia = entidad.clave_idempotencia
    modelo.folio = entidad.folio
    modelo.token = entidad.token
    modelo.rut_emisor = entidad.rut_emisor
    modelo.rut_receptor = entidad.rut_receptor
    modelo.razon_social_receptor = entidad.razon_social_receptor
    modelo.giro_receptor = entidad.giro_receptor
    modelo.direccion_receptor = entidad.direccion_receptor
    modelo.comuna_receptor = entidad.comuna_receptor
    modelo.monto_neto = entidad.monto_neto
    modelo.iva = entidad.iva
    modelo.monto_total = entidad.monto_total
    modelo.fecha_emision = entidad.fecha_emision
    modelo.error = entidad.error
    modelo.pdf = entidad.pdf
    modelo.creado_en = entidad.creado_en


def _a_tipo(codigo: int) -> TipoDocumentoTributario:
    return (
        TipoDocumentoTributario.BOLETA
        if int(codigo) == TipoDocumentoTributario.BOLETA.codigo_dte
        else TipoDocumentoTributario.FACTURA
    )
