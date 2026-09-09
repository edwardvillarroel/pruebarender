from typing import Any

from app.domain.interfaces.repositories import SolicitudDisenoRepository


class EvaluarSolicitud:
    """Caso de uso: aprobar o rechazar una solicitud de diseño (admin)."""

    def __init__(self, repositorio: SolicitudDisenoRepository) -> None:
        self._repositorio = repositorio

    def aprobar(self, solicitud_id: Any, precio: int) -> Any:
        raise NotImplementedError

    def rechazar(self, solicitud_id: Any, motivo: str) -> Any:
        raise NotImplementedError

    def listar(self) -> list[Any]:
        raise NotImplementedError