"""Purga de cotizaciones vencidas y sus archivos de imagen (A.8.10).

La política pública declara 12 meses de retención para cotizaciones no
concretadas. Este servicio:

1. Borra las filas de `solicitudes_diseno` anteriores al plazo que NO tienen
   pedido asociado (`pedidos.cotizacion_id`); las concretadas no se tocan.
2. Elimina el archivo de cada fila borrada (solo rutas locales relativas;
   `None` y URLs `http(s)://` se ignoran; un archivo ya inexistente no es
   error).
3. Limpia los huérfanos de `uploads/cotizaciones/`: archivos con `mtime` más
   viejo que el plazo y sin fila restante que los referencie.

Se invoca desde el cron semanal (`POST /api/admin/cotizaciones/purgar`) y
desde el CLI `scripts/purgar_cotizaciones.py`. `dry_run=True` solo cuenta.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from flask import current_app

from app.config import Config
from app.domain.time import utcnow


class PurgadorCotizaciones:
    def __init__(self, repo, carpeta_uploads=None):
        self.repo = repo
        self._carpeta_uploads = carpeta_uploads

    def ejecutar(self, edad_dias: int = 365, dry_run: bool = False) -> dict:
        """Aplica la retención y devuelve conteos de lo borrado (o por borrar)."""
        cutoff = utcnow() - timedelta(days=edad_dias)
        vencidas = self.repo.listar_vencidas(cutoff)
        ids = [v.id for v in vencidas]

        if not dry_run and ids:
            self.repo.eliminar(ids)

        archivos = 0
        rutas_tocadas: set[Path] = set()
        for entidad in vencidas:
            destino = self._archivo_local(entidad.imagen)
            if destino is None:
                continue
            rutas_tocadas.add(destino)
            if destino.is_file():
                archivos += 1
                if not dry_run:
                    self._borrar(destino)

        huerfanos = self._limpiar_huerfanos(cutoff, rutas_tocadas, dry_run)

        resultado = {
            "filas": len(ids),
            "archivos": archivos,
            "huerfanos": huerfanos,
            "dry_run": bool(dry_run),
        }
        current_app.logger.info(
            "[purge-cotizaciones] filas=%s archivos=%s huerfanos=%s "
            "dry_run=%s edad_dias=%s",
            resultado["filas"],
            resultado["archivos"],
            resultado["huerfanos"],
            resultado["dry_run"],
            edad_dias,
        )
        return resultado

    def eliminar_solicitud(self, entidad) -> None:
        """Borra una fila puntual y su archivo (borrado manual del admin)."""
        destino = self._archivo_local(entidad.imagen)
        if destino is not None and destino.is_file():
            self._borrar(destino)
        self.repo.eliminar([entidad.id])

    def _carpeta(self) -> Path:
        if self._carpeta_uploads is not None:
            return Path(self._carpeta_uploads)
        return Path(current_app.config.get("UPLOAD_FOLDER") or Config.UPLOAD_FOLDER)

    def _archivo_local(self, ruta) -> Path | None:
        """Ruta en disco solo para rutas relativas locales; `None`/http no aplican."""
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
            # Anti path-traversal: la ruta de la fila debe quedar dentro de uploads.
            destino.resolve().relative_to(base)
        except ValueError:
            return None
        return destino

    def _limpiar_huerfanos(
        self, cutoff, rutas_tocadas: set[Path], dry_run: bool
    ) -> int:
        carpeta = self._carpeta() / "cotizaciones"
        if not carpeta.is_dir():
            return 0
        referencias = set()
        for entidad in self.repo.listar_todos():
            if entidad.imagen and isinstance(entidad.imagen, str):
                referencias.add(entidad.imagen.replace("\\", "/"))
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
                    continue  # demasiado reciente para el plazo
            except OSError:
                continue
            huerfanos += 1
            if not dry_run:
                self._borrar(archivo)
        return huerfanos

    @staticmethod
    def _borrar(archivo: Path) -> None:
        try:
            archivo.unlink()
        except OSError:
            # Disco efímero o permisos: la purga no debe abortar por un archivo.
            current_app.logger.warning(
                "[purge-cotizaciones] no se pudo borrar %s", archivo
            )
