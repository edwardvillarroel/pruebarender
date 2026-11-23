"""Sube al bucket público `catalogo` las fotos que hoy viven en la BD.

Uso (con el venv del proyecto):
    python scripts/backfill_catalogo_storage.py --listar
    python scripts/backfill_catalogo_storage.py --limit 100

Idempotente: solo toca filas sin `imagen_url`. El bucket privado Cotizaciones
no se menciona. Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en `.env`.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg2
import requests

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

TIMEOUT = 30
MAPA_EXTENSIONES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def cargar_env() -> None:
    env = RAIZ / ".env"
    if not env.exists():
        return
    for linea in env.read_text(encoding="utf-8", errors="replace").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        # El .env del proyecto manda: una variable de sistema vieja (por ejemplo
        # un SUPABASE_URL de otro proyecto) no debe ganar por setdefault.
        os.environ[clave.strip()] = valor.strip().strip("'\"")


def extension(content_type: str | None) -> str:
    return MAPA_EXTENSIONES.get((content_type or "").lower().strip(), ".jpg")


def url_publica(base: str, ruta: str) -> str:
    return f"{base}/storage/v1/object/public/catalogo/{ruta.lstrip('/')}"


def subir(base: str, clave: str, ruta: str, datos: bytes, content_type: str) -> bool:
    respuesta = requests.post(
        f"{base}/storage/v1/object/catalogo/{ruta.lstrip('/')}",
        headers={
            "apikey": clave,
            "Authorization": f"Bearer {clave}",
            "Content-Type": content_type or "application/octet-stream",
            "x-upsert": "true",
        },
        data=datos,
        timeout=TIMEOUT,
    )
    if respuesta.ok:
        return True
    print(f"  error subiendo {ruta}: HTTP {respuesta.status_code} {respuesta.text[:160]}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--listar", action="store_true", help="Solo muestra cuántas filas faltan")
    args = parser.parse_args()

    cargar_env()
    url_db = os.environ.get("DATABASE_URL", "")
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    clave = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url_db or not base or not clave:
        print("Faltan DATABASE_URL, SUPABASE_URL o SUPABASE_SERVICE_KEY", file=sys.stderr)
        return 1

    conexion = psycopg2.connect(url_db)
    try:
        with conexion.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM productos "
                "WHERE imagen_bytes IS NOT NULL AND (imagen_url IS NULL OR imagen_url = '')"
            )
            n_productos = cur.fetchone()[0]
            cur.execute(
                "SELECT count(*) FROM producto_colores "
                "WHERE imagen_bytes IS NOT NULL AND (imagen_url IS NULL OR imagen_url = '')"
            )
            n_colores = cur.fetchone()[0]
        print(f"Pendientes: {n_productos} productos, {n_colores} colores")
        if args.listar:
            return 0

        from app.infrastructure.imagenes.thumbnail import generar_thumbnail

        with conexion.cursor() as cur:
            cur.execute(
                "SELECT id, imagen_bytes, imagen_content_type FROM productos "
                "WHERE imagen_bytes IS NOT NULL AND (imagen_url IS NULL OR imagen_url = '') "
                "LIMIT %s",
                (args.limit,),
            )
            filas = cur.fetchall()
        for producto_id, datos, content_type in filas:
            ruta = f"productos/{producto_id}{extension(content_type)}"
            if subir(base, clave, ruta, datos, content_type or "image/jpeg"):
                with conexion.cursor() as cur:
                    cur.execute(
                        "UPDATE productos SET imagen_url = %s WHERE id = %s",
                        (url_publica(base, ruta), producto_id),
                    )
                conexion.commit()
                print(f"producto {producto_id}: ok")

        with conexion.cursor() as cur:
            cur.execute(
                "SELECT id, imagen_bytes, imagen_content_type, "
                "imagen_thumb_bytes, imagen_thumb_content_type "
                "FROM producto_colores "
                "WHERE imagen_bytes IS NOT NULL AND (imagen_url IS NULL OR imagen_url = '') "
                "LIMIT %s",
                (args.limit,),
            )
            filas = cur.fetchall()
        for color_id, datos, content_type, thumb, thumb_type in filas:
            ruta = f"colores/{color_id}{extension(content_type)}"
            if not subir(base, clave, ruta, datos, content_type or "image/jpeg"):
                continue
            ruta_thumb = f"colores/{color_id}-thumb.jpg"
            thumb_ok = False
            if thumb:
                thumb_ok = subir(base, clave, ruta_thumb, thumb, thumb_type or "image/jpeg")
            else:
                generado = generar_thumbnail(datos, content_type or "image/jpeg")
                if generado:
                    thumb_ok = subir(base, clave, ruta_thumb, generado[0], generado[1])
            with conexion.cursor() as cur:
                cur.execute(
                    "UPDATE producto_colores SET imagen_url = %s, imagen_thumb_url = %s "
                    "WHERE id = %s",
                    (
                        url_publica(base, ruta),
                        url_publica(base, ruta_thumb) if thumb_ok else None,
                        color_id,
                    ),
                )
            conexion.commit()
            print(f"color {color_id}: ok")
    finally:
        conexion.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
