from __future__ import annotations
import io
import os
from typing import Any, Dict, Optional
import requests

class ClienteCotizadorIA:
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30, api_key: Optional[str] = None):
        self.base_url = (base_url or os.getenv("COTIZADOR_IA_URL") or "http://127.0.0.1:8000").rstrip("/")
        self.timeout = timeout
        self.api_key = api_key or os.getenv("APOLO_API_KEY") or ""

    def estimar(
        self,
        imagen_bytes: bytes,
        filename: str,
        alto: float = 10,
        ancho: float = 10,
        largo: float = 10,
        unidad: str = "cm",
        cantidad: int = 1,
        uso: str = "Decorativo",
        material_usuario: Optional[str] = None,
        color: str = "Negro"
    ) -> Dict[str, Any]:

        files = {
            "file": (filename or "imagen.jpg", io.BytesIO(imagen_bytes), "image/jpeg"),
        }
        data = {
            "alto": str(alto),
            "ancho": str(ancho),
            "largo": str(largo),
            "unidad": unidad,
            "cantidad": str(cantidad),
            "uso": uso,
            "color": color,
        }
        if material_usuario and material_usuario.strip().lower() not in ["no lo se", "no estoy seguro"]:
            data["material_usuario"] = material_usuario.strip()

        headers = {
            "x-apolo-key": self.api_key
        }

        resp = requests.post(f"{self.base_url}/cotizar", files=files, data=data, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        body = resp.json()

        if not isinstance(body, dict):
            raise ValueError("Respuesta de cotizador inválida")

        def _num(v, minimo=None, maximo=None):
            try:
                n = float(v)
            except (TypeError, ValueError):
                return None
            if n != n or n in (float("inf"), float("-inf")):
                return None
            if minimo is not None and n < minimo:
                return None
            if maximo is not None and n > maximo:
                return None
            return n

        return {
            "precio_estimado_ia": _num(body.get("precio_clp"), 0, 9999999999.99),
            "precio_unitario_ia": _num(body.get("precio_unitario_clp"), 0, 9999999999.99),
            "gramos_estimados_ia": _num(body.get("gramos_estimados"), 0, 1000000),
            "tiempo_estimado_horas_ia": _num(body.get("tiempo_estimado_horas"), 0, 10000),
            "material_sugerido_ia": str(body.get("material_detectado") or "")[:50] or None,
            "complejidad_ia": str(body.get("complejidad") or "")[:50] or None,
            "confianza_material_ia": _num(body.get("confianza_material"), 0, 1),
            "confianza_complejidad_ia": _num(body.get("confianza_complejidad"), 0, 1),
            "detalle": str(body.get("detalle") or "")[:500] or None,
        }