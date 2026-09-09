from typing import Any

from app.domain.interfaces.repositories import SolicitudDisenoRepository


class CrearSolicitud:
    """Caso de uso: registrar una solicitud de diseño personalizado.

    El input del formulario debe pasar por sanitizacion antes de persistirse
    y de cualquier contacto con el LLM (RNF-05).
    """

    def __init__(self, repositorio: SolicitudDisenoRepository) -> None:
        self._repositorio = repositorio

    def ejecutar(self, dto: Any, imagen: Any = None) -> Any:
        raise NotImplementedError