from pathlib import Path
from uuid import uuid4


def guardar_imagen_cotizacion(contenido: bytes, extension: str, carpeta_base) -> str:
    carpeta = Path(carpeta_base) / "cotizaciones"
    carpeta.mkdir(parents=True, exist_ok=True)
    ext = extension if extension.startswith(".") else f".{extension}"
    nombre = f"{uuid4().hex}{ext}"
    ruta = carpeta / nombre
    with open(ruta, "wb") as f:
        f.write(contenido)
    return f"cotizaciones/{nombre}"
