



from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import current_app

from app.config import Config
from app.domain.time import utcnow


class PurgadorCotizaciones:
    def __init__(self, repo, carpeta_uploads=None, almacen=None):
        self.repo = repo
        self._carpeta_uploads = carpeta_uploads
        self._almacen_param = almacen

    def ejecutar(self, edad_dias: int = 365, dry_run: bool = False) -> dict:
        cutoff = utcnow() - timedelta(days=edad_dias)
        vencidas = self.repo.listar_vencidas(cutoff)
        ids = [v.id for v in vencidas]

        if not dry_run and ids:
            self.repo.eliminar(ids)

        almacen = self._almacen()
        archivos = 0
        archivos_bucket = 0
        rutas_tocadas: set[Path] = set()
        bucket_tocadas: set[str] = set()
        for entidad in vencidas:
            bucket_ruta = self._ruta_bucket(entidad.imagen)
            if bucket_ruta is not None and almacen is not None:
                bucket_tocadas.add(bucket_ruta)
                if dry_run:
                    if almacen.existe(bucket_ruta):
                        archivos_bucket += 1
                elif almacen.eliminar(bucket_ruta):
                    archivos_bucket += 1
            self._borrar_miniatura(almacen, entidad.imagen, dry_run)
            destino = self._archivo_local(entidad.imagen)
            if destino is None:
                continue
            rutas_tocadas.add(destino)
            if destino.is_file():
                archivos += 1
                if not dry_run:
                    self._borrar(destino)

        referencias = self._referencias()
        huerfanos = self._limpiar_huerfanos(
            cutoff, rutas_tocadas, dry_run, referencias
        )
        huerfanos_bucket = self._limpiar_huerfanos_bucket(
            cutoff, bucket_tocadas, dry_run, referencias
        )

        resultado = {
            "filas": len(ids),
            "archivos": archivos,
            "archivos_bucket": archivos_bucket,
            "huerfanos": huerfanos,
            "huerfanos_bucket": huerfanos_bucket,
            "dry_run": bool(dry_run),
        }
        current_app.logger.info(
            "[purge-cotizaciones] filas=%s archivos=%s archivos_bucket=%s "
            "huerfanos=%s huerfanos_bucket=%s dry_run=%s edad_dias=%s",
            resultado["filas"],
            resultado["archivos"],
            resultado["archivos_bucket"],
            resultado["huerfanos"],
            resultado["huerfanos_bucket"],
            resultado["dry_run"],
            edad_dias,
        )
        return resultado

    def eliminar_solicitud(self, entidad) -> None:
        almacen = self._almacen()
        bucket_ruta = self._ruta_bucket(entidad.imagen)
        if almacen is not None and bucket_ruta is not None:
            almacen.eliminar(bucket_ruta)
        self._borrar_miniatura(almacen, entidad.imagen)
        destino = self._archivo_local(entidad.imagen)
        if destino is not None and destino.is_file():
            self._borrar(destino)
        self.repo.eliminar([entidad.id])

    def _borrar_miniatura(self, almacen, ruta, dry_run: bool = False) -> None:

        if dry_run:
            return
        from app.infrastructure.imagenes.miniaturas_cotizacion import ruta_miniatura

        destino = ruta_miniatura(self._ruta_bucket(ruta))
        if destino is None:
            return
        if almacen is not None and getattr(almacen, "configurado", False):
            almacen.eliminar(destino)
        base = self._carpeta().resolve()
        archivo = base / destino
        try:
            archivo.resolve().relative_to(base)
        except (OSError, ValueError):
            return
        if archivo.is_file():
            self._borrar(archivo)

    def _almacen(self):
        if self._almacen_param is not None:
            return self._almacen_param
        try:
            from app.infrastructure.storage.supabase_storage import (
                almacen_desde_config,
            )

            return almacen_desde_config()
        except Exception:  # noqa: BLE001 - la purga no puede caer por configuración
            current_app.logger.warning(
                "[purge-cotizaciones] no se pudo resolver el almacen de Supabase"
            )
            return None

    def _carpeta(self) -> Path:
        if self._carpeta_uploads is not None:
            return Path(self._carpeta_uploads)
        return Path(current_app.config.get("UPLOAD_FOLDER") or Config.UPLOAD_FOLDER)

    def _archivo_local(self, ruta) -> Path | None:
        if not ruta or not isinstance(ruta, str):
            return None
        if ruta.startswith(("http://", "https://")):
            return None
        normalizada = ruta.replace("\\", "/")
        if normalizada.startswith("/"):
            return None
        base = self._carpeta().resolve()
        destino = base / normalizada
        try:
            destino.resolve().relative_to(base)
        except ValueError:
            return None
        return destino

    @staticmethod
    def _ruta_bucket(ruta) -> str | None:

        if not ruta or not isinstance(ruta, str):
            return None
        normalizada = ruta.replace("\\", "/")
        if normalizada.startswith(("http://", "https://", "/")):
            return None
        if ".." in normalizada.split("/"):
            return None
        return normalizada

    def _referencias(self) -> set[str]:
        referencias = set()
        for entidad in self.repo.listar_todos():
            ruta = self._ruta_bucket(entidad.imagen)
            if ruta is not None:
                referencias.add(ruta)
        return referencias

    def _limpiar_huerfanos(
        self, cutoff, rutas_tocadas: set[Path], dry_run: bool, referencias: set[str]
    ) -> int:
        carpeta = self._carpeta() / "cotizaciones"
        if not carpeta.is_dir():
            return 0
        corte_ts = cutoff.timestamp()
        tocadas = {p.resolve() for p in rutas_tocadas}
        huerfanos = 0
        for archivo in carpeta.iterdir():
            if not archivo.is_file():
                continue
            if f"cotizaciones/{archivo.name}" in referencias:
                continue
            if archivo.resolve() in tocadas:
                continue
            try:
                if archivo.stat().st_mtime >= corte_ts:
                    continue
            except OSError:
                continue
            huerfanos += 1
            if not dry_run:
                self._borrar(archivo)
        return huerfanos

    def _limpiar_huerfanos_bucket(
        self, cutoff, tocadas: set[str], dry_run: bool, referencias: set[str]
    ) -> int:

        almacen = self._almacen()
        if almacen is None or not almacen.configurado:
            return 0
        try:
            objetos = almacen.listar("cotizaciones/")
        except Exception:  # noqa: BLE001 - el bucket no rompe la purga
            current_app.logger.warning(
                "[purge-cotizaciones] no se pudo listar el bucket de cotizaciones"
            )
            return 0
        huerfanos = 0
        for objeto in objetos:
            if not isinstance(objeto, dict):
                continue
            nombre = objeto.get("name")
            if not nombre or not isinstance(nombre, str):
                continue
            if nombre in referencias or nombre in tocadas:
                continue
            creado = _fecha_storage(objeto.get("created_at"))
            if creado is None or creado >= cutoff:
                continue
            huerfanos += 1
            if not dry_run:
                almacen.eliminar(nombre)
        return huerfanos

    @staticmethod
    def _borrar(archivo: Path) -> None:
        try:
            archivo.unlink()
        except OSError:
            current_app.logger.warning(
                "[purge-cotizaciones] no se pudo borrar %s", archivo
            )


def _fecha_storage(valor):
    if not valor or not isinstance(valor, str):
        return None
    try:
        fecha = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha
