from typing import Any

from app.domain.interfaces.repositories import SolicitudDisenoRepository


class CrearSolicitud:


    def __init__(self, repositorio: SolicitudDisenoRepository) -> None:
        self._repositorio = repositorio

    def ejecutar(self, dto: Any, imagen: Any = None) -> Any:
        raise NotImplementedError