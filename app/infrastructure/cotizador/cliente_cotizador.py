from __future__ import annotations
import io
import os
from typing import Any, Dict, Optional
import requests

class ClienteCotizadorIA:
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        self.base_url = (base_url or os.getenv("COTIZADOR_IA_URL") or "http://127.0.0.1:8000").rstrip("/")
        self.timeout = timeout

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

        resp = requests.post(f"{self.base_url}/cotizar", files=files, data=data, timeout=self.timeout)
        resp.raise_for_status()
        body = resp.json()
        print("[COTIZADOR] Respuesta:", body)
        

        return {
            "precio_estimado_ia": body.get("precio_clp"),
            "precio_unitario_ia": body.get("precio_unitario_clp"),
            "gramos_estimados_ia": body.get("gramos_estimados"),
            "tiempo_estimado_horas_ia": body.get("tiempo_estimado_horas"),
            "material_sugerido_ia": body.get("material_detectado"),
            "complejidad_ia": body.get("complejidad"),
            "confianza_material_ia": body.get("confianza_material"),
            "confianza_complejidad_ia": body.get("confianza_complejidad"),
            "detalle": body.get("detalle"),
            **body
        }