from uuid import UUID

from app.domain.entities.log_auditoria import LogAuditoria


class GestionAuditoria:


    def __init__(self, registro) -> None:
        self._registro = registro

    def registrar(
        self,
        accion: str,
        *,
        entidad_tipo: str,
        entidad_id: str | None = None,
        usuario_id=None,
        detalle: str | None = None,
        ip: str | None = None,
    ) -> None:
        log = LogAuditoria(
            accion=accion,
            entidad_tipo=entidad_tipo,
            entidad_id=entidad_id,
            usuario_id=_como_uuid(usuario_id),
            detalle=detalle,
            ip=ip,
        )
        self._registro.add(log)


def _como_uuid(valor):
    if isinstance(valor, str):
        try:
            return UUID(valor)
        except ValueError:
            return None
    return valor
