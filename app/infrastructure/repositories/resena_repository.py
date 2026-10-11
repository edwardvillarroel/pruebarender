from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.domain.entities.resena import Resena, ResenaPublica
from app.domain.interfaces.repositories import (
    ResenaDuplicadaError,
    ResenaRepository as ResenaRepositoryInterface,
)
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.producto_model import ProductoModel
from app.infrastructure.database.models.resena_model import ResenaModel
from app.infrastructure.database.models.usuario_model import UsuarioModel


class ResenaRepository(ResenaRepositoryInterface):
    model = ResenaModel

    def get_by_id(self, entity_id: UUID) -> Resena | None:
        modelo = db.session.get(self.model, entity_id)
        return _a_entidad(modelo) if modelo else None

    def list(self, *filters: Any) -> list[Resena]:
        consulta = db.session.query(self.model)
        if filters:
            consulta = consulta.filter(*filters)
        return [_a_entidad(m) for m in consulta.all()]

    def crear(self, entidad: Resena) -> Resena:
        """INSERT + recálculo de stats en la MISMA transacción.

        El `flush` previo al UPDATE hace que el promedio ya incluya la reseña
        nueva; si el `commit` revienta por el `UNIQUE` (doble submit o dos
        pestañas), el rollback deshace también el UPDATE: nunca queda un
        `rating` inflado sin la fila que lo justifica.
        """
        try:
            db.session.add(_a_modelo(entidad))
            db.session.flush()
            self._recalcular_stats(entidad.producto_id)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            # Mismo idiom que `PagoRepository.add`: si el triple ya existía es
            # el duplicado de negocio; cualquier otro fallo de integridad se
            # propaga tal cual (una mentira en el 409 es peor que un 500).
            if (
                self.obtener(
                    entidad.usuario_id, entidad.pedido_id, entidad.producto_id
                )
                is not None
            ):
                raise ResenaDuplicadaError(
                    "El producto ya tiene una reseña tuya en este pedido"
                ) from None
            raise
        return entidad

    def add(self, entidad: Resena) -> Resena:
        """Contrato de `RepositoryBase` (insertar). Las reseñas pasan por
        `crear`, que inserta Y recalcula los stats, así que `add` delega: un
        INSERT sin recálculo dejaría `rating`/`resenas_count` desincronizados.
        """
        return self.crear(entidad)

    def listar_por_pedido(self, pedido_id: UUID) -> list[Resena]:
        modelos = db.session.execute(
            select(self.model)
            .where(self.model.pedido_id == pedido_id)
            .order_by(self.model.creado_en, self.model.id)
        ).scalars().all()
        return [_a_entidad(m) for m in modelos]

    def listar_por_producto(self, producto_id: UUID) -> list[ResenaPublica]:
        """JOIN con `usuarios` para armar el nombre a mostrar sin exponer el id."""
        filas = db.session.execute(
            select(self.model, UsuarioModel)
            .join(UsuarioModel, UsuarioModel.id == self.model.usuario_id)
            .where(self.model.producto_id == producto_id)
            .order_by(self.model.creado_en.desc(), self.model.id)
        ).all()
        return [_a_resena_publica(modelo, usuario) for modelo, usuario in filas]

    def obtener(
        self, usuario_id: UUID, pedido_id: UUID, producto_id: UUID
    ) -> Resena | None:
        modelo = db.session.execute(
            select(self.model).where(
                self.model.usuario_id == usuario_id,
                self.model.pedido_id == pedido_id,
                self.model.producto_id == producto_id,
            )
        ).scalar_one_or_none()
        return _a_entidad(modelo) if modelo else None

    def recalcular_stats_producto(self, producto_id: UUID) -> None:
        """Re-sincroniza `rating`/`resenas_count` desde las filas de `resenas`.

        Camino de reparación (re-seed); el recálculo en vivo ya corre dentro
        de `crear`.
        """
        self._recalcular_stats(producto_id)
        db.session.commit()

    def update(self, entidad: Resena) -> Resena:
        raise NotImplementedError("Las reseñas son inmutables en v1 (sin edición)")

    def delete(self, entidad: Resena) -> None:
        raise NotImplementedError("Las reseñas son inmutables en v1 (sin borrado)")

    def _recalcular_stats(self, producto_id: UUID) -> None:
        cantidad = (
            select(func.count())
            .select_from(ResenaModel)
            .where(ResenaModel.producto_id == producto_id)
            .scalar_subquery()
        )
        promedio = (
            select(func.round(func.avg(ResenaModel.estrellas), 1))
            .where(ResenaModel.producto_id == producto_id)
            .scalar_subquery()
        )
        db.session.execute(
            update(ProductoModel)
            .where(ProductoModel.id == producto_id)
            .values(resenas_count=cantidad, rating=promedio)
        )


def _a_entidad(modelo: ResenaModel) -> Resena:
    return Resena(
        id=modelo.id,
        usuario_id=modelo.usuario_id,
        pedido_id=modelo.pedido_id,
        producto_id=modelo.producto_id,
        estrellas=int(modelo.estrellas),
        comentario=modelo.comentario,
        creado_en=modelo.creado_en,
        actualizado_en=modelo.actualizado_en,
    )


def _a_modelo(entidad: Resena) -> ResenaModel:
    return ResenaModel(
        id=entidad.id,
        usuario_id=entidad.usuario_id,
        pedido_id=entidad.pedido_id,
        producto_id=entidad.producto_id,
        estrellas=entidad.estrellas,
        comentario=entidad.comentario,
        creado_en=entidad.creado_en,
        actualizado_en=entidad.actualizado_en,
    )


def _nombre_a_mostrar(nombre: str | None, apellido: str | None) -> str:
    """`"Nombre A."` con inicial del apellido; cae a `nombre` o a `"Cliente"`.

    `nombre`/`apellido` son columnas NOT NULL, pero pueden venir vacias (p. ej.
    cuentas creadas por otro medio): aca se les da una salida decente en la
    vista publica en vez de exponer un nombre en blanco.
    """
    nombre = (nombre or "").strip()
    apellido = (apellido or "").strip()
    if not nombre:
        return "Cliente"
    if not apellido:
        return nombre
    return f"{nombre} {apellido[0]}."


def _a_resena_publica(modelo: ResenaModel, usuario: UsuarioModel) -> ResenaPublica:
    return ResenaPublica(
        id=modelo.id,
        producto_id=modelo.producto_id,
        estrellas=int(modelo.estrellas),
        comentario=modelo.comentario,
        creado_en=modelo.creado_en,
        autor=_nombre_a_mostrar(usuario.nombre, usuario.apellido),
    )
