from app.domain.entities.log_auditoria import LogAuditoria
from app.infrastructure.database.connection import db
from app.infrastructure.database.models.log_auditoria_model import LogAuditoriaModel


class LogAuditoriaRepository:
    """Repositorio BD de eventos de auditoria (RNF-06)."""

    model = LogAuditoriaModel

    def add(self, log: LogAuditoria) -> LogAuditoria:
        """INSERT del evento de auditoria."""
        db.session.add(
            LogAuditoriaModel(
                id=log.id,
                usuario_id=log.usuario_id,
                accion=log.accion,
                entidad_tipo=log.entidad_tipo,
                entidad_id=log.entidad_id,
                detalle=log.detalle,
                ip=log.ip,
                creado_en=log.creado_en,
            )
        )
        db.session.commit()
        return log
