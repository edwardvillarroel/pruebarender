"""Verifica que el catálogo público siga legible y el resto cerrado para anon.

Uso (con el venv del proyecto):
    python scripts/probe_rls.py
    python scripts/probe_rls.py --url https://<proyecto>.supabase.co --anon-key sb_publishable_...

La anon key es pública; se puede pasar por CLI. Si no se entrega, se busca en
SUPABASE_ANON_KEY / VITE_SUPABASE_ANON_KEY y, como último recurso, en el
.env.production del front hermano (configurable con --front-env).

El probe es de solo lectura: el único POST es un INSERT con precio inválido,
rechazado antes de escribir. No necesita la service_role.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys

import requests

RAIZ = pathlib.Path(__file__).resolve().parent.parent
TIMEOUT = 20

PUBLICAS = ("productos", "categorias", "producto_colores")
CERRADAS = (
    "usuarios",
    "pedidos",
    "pagos",
    "detalle_pedidos",
    "carrito",
    "carrito_items",
    "refresh_tokens",
    "codigos_verificacion",
    "codigos_respaldo",
    "sesiones_venta",
    "bloqueos_login",
    "solicitudes_diseno",
    "logs_seguridad",
    "logs_auditoria",
    "notificaciones",
    "ventas_local",
    "venta_local_items",
    "cupones",
    "documentos_tributarios",
    "resenas",
)


def cargar_env(ruta: pathlib.Path) -> None:
    """El .env del proyecto manda sobre variables de sistema obsoletas."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        os.environ[clave.strip()] = valor.strip().strip("'\"")


def resolver_anon_key(explicita: str | None, front_env: pathlib.Path) -> str | None:
    if explicita:
        return explicita.strip()
    # El .env.production del front manda: es la key realmente desplegada. Hay
    # variables de sistema heredadas de otros proyectos que de otro modo
    # ganarían por orden y harían que el probe probe el proyecto equivocado.
    if front_env.exists():
        for linea in front_env.read_text(encoding="utf-8", errors="replace").splitlines():
            if linea.startswith("VITE_SUPABASE_ANON_KEY="):
                return linea.partition("=")[2].strip().strip("'\"")
    for nombre in ("SUPABASE_ANON_KEY", "VITE_SUPABASE_ANON_KEY"):
        if os.environ.get(nombre):
            return os.environ[nombre].strip()
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="SUPABASE_URL (por defecto, la del .env)")
    parser.add_argument("--anon-key", help="anon/publishable key (pública)")
    parser.add_argument(
        "--front-env",
        type=pathlib.Path,
        default=RAIZ.parent / "apolovibes-front" / ".env.production",
        help="Ruta al .env.production del front, si no hay anon key en el entorno",
    )
    args = parser.parse_args()

    cargar_env(RAIZ / ".env")
    url = (args.url or os.environ.get("SUPABASE_URL") or "").rstrip("/")
    anon = resolver_anon_key(args.anon_key, args.front_env)
    if not url or not anon:
        parser.error("Faltan SUPABASE_URL o la anon key (--anon-key / SUPABASE_ANON_KEY / --front-env)")

    headers = {"apikey": anon, "Authorization": f"Bearer {anon}"}
    rest = f"{url}/rest/v1"
    storage = f"{url}/storage/v1/object/list"
    fallos: list[str] = []
    total = 0

    def verificar(nombre: str, ok: bool, detalle: str = "") -> None:
        nonlocal total
        total += 1
        estado = "PASS" if ok else "FAIL"
        print(f"[{estado}] {nombre}" + (f" — {detalle}" if detalle else ""))
        if not ok:
            fallos.append(nombre)

    def get_json(ruta: str):
        return requests.get(rest + ruta, headers=headers, timeout=TIMEOUT)

    # P0/P1: catálogo legible.
    for tabla in PUBLICAS:
        try:
            res = get_json(f"/{tabla}?select=*&limit=1")
            filas = res.json() if res.status_code == 200 else []
            verificar(f"lectura pública de {tabla}", res.status_code == 200 and len(filas) > 0,
                      f"HTTP {res.status_code}, filas={len(filas)}")
        except requests.RequestException as exc:
            verificar(f"lectura pública de {tabla}", False, str(exc))

    # P0: los productos ocultos dejan de ser visibles para anon.
    try:
        res = get_json("/productos?select=*&activo=eq.false&limit=1")
        filas = res.json() if res.status_code == 200 else []
        verificar("productos inactivos NO visibles", res.status_code == 200 and len(filas) == 0,
                  f"HTTP {res.status_code}, filas={len(filas)}")
    except requests.RequestException as exc:
        verificar("productos inactivos NO visibles", False, str(exc))

    # P1: el resto de tablas públicas no tienen SELECT para anon.
    for tabla in CERRADAS:
        try:
            res = get_json(f"/{tabla}?select=*&limit=1")
            # 404 = la tabla no existe en este proyecto; también está cerrada.
            verificar(f"{tabla} cerrada para anon", res.status_code in (401, 403, 404),
                      f"HTTP {res.status_code}")
        except requests.RequestException as exc:
            verificar(f"{tabla} cerrada para anon", False, str(exc))

    # P1: anon no puede escribir en el catálogo. Precio inválido => nunca se inserta.
    try:
        res = requests.post(
            f"{rest}/productos",
            headers={**headers, "Content-Type": "application/json"},
            json={"nombre": "__probe_rls__", "precio": "no-valido"},
            timeout=TIMEOUT,
        )
        verificar("escritura anon bloqueada", res.status_code in (401, 403), f"HTTP {res.status_code}")
    except requests.RequestException as exc:
        verificar("escritura anon bloqueada", False, str(exc))

    # Bucket público: lectura de catálogo permitida.
    try:
        res = requests.post(
            f"{storage}/catalogo",
            headers={**headers, "Content-Type": "application/json"},
            json={"prefix": "", "limit": 1, "offset": 0},
            timeout=TIMEOUT,
        )
        verificar("bucket catalogo legible", res.status_code == 200, f"HTTP {res.status_code}")
    except requests.RequestException as exc:
        verificar("bucket catalogo legible", False, str(exc))

    print(f"\n{total - len(fallos)}/{total} checks OK")
    if fallos:
        print("Fallos: " + ", ".join(fallos), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
