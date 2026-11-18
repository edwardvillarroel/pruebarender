




from __future__ import annotations

from pathlib import Path

from flask import current_app

from app.config import Config


class MigradorCotizaciones:
    def __init__(self, repo, almacen, carpeta_uploads=None):
        if almacen is None or not getattr(almacen, "configurado", False):
            raise ValueError("Supabase Storage no está configurado")
        self.repo = repo
        self.almacen = almacen
        self._carpeta_uploads = carpeta_uploads

    def ejecutar(self, dry_run: bool = False) -> dict:
        resultado = {
            "migrados": 0,
            "ya_existian": 0,
            "sin_archivo_local": 0,
            "errores": 0,
            "dry_run": bool(dry_run),
        }

        for ruta, archivo in self._rutas_a_migrar().items():
            if self.almacen.existe(ruta):
                resultado["ya_existian"] += 1
                continue
            if archivo is None or not archivo.is_file():
                resultado["sin_archivo_local"] += 1
                continue
            if dry_run:
                resultado["migrados"] += 1
                continue
            try:
                contenido = archivo.read_bytes()
            except OSError as exc:
                current_app.logger.warning(
                    "[migrar-cotizaciones] no se pudo leer %s: %s", archivo, exc
                )
                resultado["errores"] += 1
                continue
            if self.almacen.subir(ruta, contenido, _tipo_mime(archivo.suffix)):
                resultado["migrados"] += 1
            else:
                resultado["errores"] += 1

        current_app.logger.info(
            "[migrar-cotizaciones] migrados=%s ya_existian=%s "
            "sin_archivo_local=%s errores=%s dry_run=%s",
            resultado["migrados"],
            resultado["ya_existian"],
            resultado["sin_archivo_local"],
            resultado["errores"],
            resultado["dry_run"],
        )
        return resultado

    def _rutas_a_migrar(self) -> dict[str, Path | None]:

        rutas: dict[str, Path | None] = {}

        carpeta = self._carpeta() / "cotizaciones"
        if carpeta.is_dir():
            for archivo in carpeta.iterdir():
                if archivo.is_file():
                    rutas[f"cotizaciones/{archivo.name}"] = archivo

        for entidad in self.repo.listar_todos():
            ruta = _ruta_migrable(entidad.imagen)
            if ruta is None or ruta in rutas:
                continue
            destino = self._ruta_local(ruta)
            rutas[ruta] = destino if destino is not None and destino.is_file() else None
        return rutas

    def _carpeta(self) -> Path:
        if self._carpeta_uploads is not None:
            return Path(self._carpeta_uploads)
        return Path(current_app.config.get("UPLOAD_FOLDER") or Config.UPLOAD_FOLDER)

    def _ruta_local(self, ruta: str) -> Path | None:
        base = self._carpeta().resolve()
        destino = base / ruta
        try:
            destino.resolve().relative_to(base)
        except ValueError:
            return None
        return destino


def _ruta_migrable(imagen) -> str | None:
    if not imagen or not isinstance(imagen, str):
        return None
    normalizada = imagen.replace("\\", "/")
    if normalizada.startswith(("http://", "https://", "/")):
        return None
    if ".." in normalizada.split("/"):
        return None
    return normalizada


def _tipo_mime(extension: str) -> str:
    from app.infrastructure.storage.supabase_storage import tipo_mime

    return tipo_mime(extension)
