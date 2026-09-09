from typing import Any


class GenerarModelo3D:
    """Caso de uso: orquestar la llamada asíncrona al LLM para generar
    un modelo 3D a partir de una imagen (image-to-3d)."""

    def iniciar(self, imagen: Any, sector: Any = None) -> Any:
        # TODO: encolar tarea Celery, retornar { taskId }
        raise NotImplementedError

    def consultar(self, task_id: str) -> Any:
        # TODO: devolver { status, modelUrl, error }
        raise NotImplementedError