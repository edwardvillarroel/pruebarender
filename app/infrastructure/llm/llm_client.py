"""Cliente HTTP del proveedor LLM.

Punto de integración aislado para poder aplicar rate limiting específico
(RNF-02) y reutilizar el proveedor elegido.
"""


class LLMClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    def generar_modelo_3d(self, imagen_path: str) -> dict:
        # TODO: POST a proveedor LLM (image-to-3d)
        raise NotImplementedError

    def consultar_estado(self, task_id: str) -> dict:
        raise NotImplementedError