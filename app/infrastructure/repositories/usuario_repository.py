from typing import Any
from uuid import UUID

from sqlalchemy import func, literal, select

from app.domain.entities.usuario import Usuario, UsuarioMetricas
from app.domain.enums import EstadoPago, EstadoPedido, EstadoSolicitudDiseno, Rol
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.detalle_pedido_model import DetallePedidoModel
from app.infrastructure.database.models.pago_model import PagoModel
from app.infrastructure.database.models.pedido_model import PedidoModel
from app.infrastructure.database.models.solicitud_diseno_model import (
    SolicitudDisenoModel,
)
from app.infrastructure.database.models.usuario_model import UsuarioModel
from app.infrastructure.repositories.repository_base import RepositoryBase


class UsuarioRepository(RepositoryBase):
    model = UsuarioModel

    def get_by_email(self, email: str) -> UsuarioModel | None:
        return self.model.query.filter_by(email=email).first()


    def buscar_por_id(self, usuario_id: UUID) -> Usuario | None:
        return _a_entidad(db.session.get(self.model, usuario_id))

    def crear(self, usuario: Usuario) -> Usuario:
        modelo = UsuarioModel(
            id=usuario.id,
            email=usuario.email,
            password_hash=usuario.password_hash,
            nombre=usuario.nombre,
            apellido=usuario.apellido,
            telefono=usuario.telefono,
            rol=_texto_rol(usuario.rol),
            activo=usuario.activo,
            auth_provider=usuario.auth_provider,
            creado_en=usuario.creado_en,
            eliminado_en=usuario.eliminado_en,
        )
        db.session.add(modelo)
        db.session.commit()
        return _a_entidad(modelo)

    def actualizar(self, usuario: Usuario) -> Usuario:

        modelo = db.session.get(self.model, usuario.id)
        if modelo is None:
            raise ValueError("Usuario no encontrado")
        modelo.rol = _texto_rol(usuario.rol)
        modelo.activo = usuario.activo
        modelo.eliminado_en = usuario.eliminado_en
        db.session.commit()
        return _a_entidad(modelo)

    def contar_admins_activos(self) -> int:
        return int(
            db.session.query(func.count(UsuarioModel.id))
            .filter(
                UsuarioModel.rol == Rol.ADMIN.value,
                UsuarioModel.activo.is_(True),
                UsuarioModel.eliminado_en.is_(None),
            )
            .scalar()
            or 0
        )

    def correo_en_uso(self, email: str) -> bool:

        normalizado = (email or "").strip().lower()
        return (
            db.session.query(UsuarioModel.id)
            .filter(func.lower(UsuarioModel.email) == normalizado)
            .first()
            is not None
        )


    def listar_con_metricas(self) -> list[UsuarioMetricas]:

        pago_completado = (
            select(literal(1))
            .select_from(PagoModel)
            .where(PagoModel.pedido_id == PedidoModel.id)
            .where(PagoModel.estado == EstadoPago.COMPLETADO.value)
        )
        compras = (
            select(
                PedidoModel.usuario_id.label("usuario_id"),
                func.coalesce(func.sum(DetallePedidoModel.cantidad), 0).label("productos"),
                func.count(func.distinct(PedidoModel.id)).label("pedidos"),
            )
            .join(DetallePedidoModel, DetallePedidoModel.pedido_id == PedidoModel.id)
            .where(PedidoModel.estado != EstadoPedido.CANCELADO.value)
            .where(pago_completado.exists())
            .group_by(PedidoModel.usuario_id)
            .subquery()
        )
        cotizaciones = (
            select(
                SolicitudDisenoModel.usuario_id.label("usuario_id"),
                func.count(SolicitudDisenoModel.id).label("pedidas"),
                func.count(SolicitudDisenoModel.id)
                .filter(SolicitudDisenoModel.estado == EstadoSolicitudDiseno.APROBADA.value)
                .label("aprobadas"),
                func.count(SolicitudDisenoModel.id)
                .filter(SolicitudDisenoModel.estado == EstadoSolicitudDiseno.RECHAZADA.value)
                .label("rechazadas"),
            )
            .group_by(SolicitudDisenoModel.usuario_id)
            .subquery()
        )

        filas = db.session.execute(
            select(
                UsuarioModel,
                func.coalesce(compras.c.productos, 0),
                func.coalesce(compras.c.pedidos, 0),
                func.coalesce(cotizaciones.c.pedidas, 0),
                func.coalesce(cotizaciones.c.aprobadas, 0),
                func.coalesce(cotizaciones.c.rechazadas, 0),
            )
            .outerjoin(compras, compras.c.usuario_id == UsuarioModel.id)
            .outerjoin(cotizaciones, cotizaciones.c.usuario_id == UsuarioModel.id)
            .where(UsuarioModel.eliminado_en.is_(None))
            .order_by(UsuarioModel.nombre, UsuarioModel.apellido, UsuarioModel.email)
        ).all()

        return [_a_metricas(fila) for fila in filas]


def _texto_rol(rol: Any) -> str:
    return rol.value if isinstance(rol, Rol) else str(rol)


def _a_entidad(modelo: UsuarioModel | None) -> Usuario | None:
    if modelo is None:
        return None
    return Usuario(
        id=modelo.id,
        email=modelo.email,
        password_hash=modelo.password_hash,
        nombre=modelo.nombre,
        apellido=modelo.apellido,
        telefono=modelo.telefono,
        rol=Rol(modelo.rol),
        activo=modelo.activo,
        auth_provider=modelo.auth_provider,
        google_sub=modelo.google_sub,
        mfa_secret=modelo.mfa_secret,
        mfa_activo=modelo.mfa_activo,
        creado_en=modelo.creado_en,
        eliminado_en=modelo.eliminado_en,
    )


def _a_metricas(fila: Any) -> UsuarioMetricas:
    usuario, productos, pedidos, pedidas, aprobadas, rechazadas = fila
    return UsuarioMetricas(
        id=usuario.id,
        nombre=usuario.nombre,
        apellido=usuario.apellido,
        email=usuario.email,
        rol=usuario.rol,
        activo=bool(usuario.activo),
        productos_comprados=int(productos or 0),
        pedidos_pagados=int(pedidos or 0),
        cotizaciones_pedidas=int(pedidas or 0),
        cotizaciones_aprobadas=int(aprobadas or 0),
        cotizaciones_rechazadas=int(rechazadas or 0),
    )
