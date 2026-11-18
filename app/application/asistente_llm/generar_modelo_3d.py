from typing import Any


class GenerarModelo3D:

    def iniciar(self, imagen: Any, sector: Any = None) -> Any:
        raise NotImplementedError

    def consultar(self, task_id: str) -> Any:
        raise NotImplementedError