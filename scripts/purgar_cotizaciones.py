"""Purga manual de cotizaciones vencidas (retención 12 meses, A.8.10).

Equivalente en local al cron semanal `POST /api/admin/cotizaciones/purgar`:
borra filas sin pedido mayores al plazo, sus archivos y los huérfanos de
`uploads/cotizaciones/`.

Uso (desde la raíz del repo):
    .venv\\Scripts\\python.exe scripts/purgar_cotizaciones.py --dry-run
    .venv\\Scripts\\python.exe scripts/purgar_cotizaciones.py --edad-dias 365
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Permite ejecutar el script desde cualquier carpeta.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.application.diseno.purgar_cotizaciones import (  # noqa: E402
    PurgadorCotizaciones,
)
from app.config import Config  # noqa: E402
from app.infrastructure.repositories.solicitud_diseno_repository import (  # noqa: E402
    SolicitudDisenoRepository,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Purga cotizaciones vencidas y sus archivos de imagen."
    )
    parser.add_argument(
        "--edad-dias",
        type=int,
        default=365,
        help="Antigüedad mínima en días para borrar (default: 365).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo cuenta lo que se borraría, no toca nada.",
    )
    args = parser.parse_args(argv)

    app = create_app(Config)
    with app.app_context():
        resultado = PurgadorCotizaciones(SolicitudDisenoRepository()).ejecutar(
            edad_dias=args.edad_dias, dry_run=args.dry_run
        )
    print(resultado)
    return 0


if __name__ == "__main__":
    sys.exit(main())
