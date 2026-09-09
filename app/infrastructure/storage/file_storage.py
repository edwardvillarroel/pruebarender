"""Almacenamiento de archivos (imágenes de cotización, modelos 3D)."""

from pathlib import Path

from flask import current_app


def guardar_archivo(archivo, subcarpeta: str) -> str:
    """Guarda un archivo subido y devuelve la ruta relativa."""
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"]) / subcarpeta
    upload_dir.mkdir(parents=True, exist_ok=True)
    ruta = upload_dir / archivo.filename
    archivo.save(ruta)
    return str(ruta)


def existe(ruta_relativa: str) -> bool:
    return (Path(current_app.config["UPLOAD_FOLDER"]) / ruta_relativa).exists()