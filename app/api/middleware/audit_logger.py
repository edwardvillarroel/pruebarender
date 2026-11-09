"""Auditoría de acciones sensibles (RNF-06).

Decorador para endpoints cuyas acciones deben quedar registradas
(en LogAuditoria). Ej: crear pedido, procesar pago, aprobar cotización.

El decorador registra la accion sobre el endpoint y, al ejecutar la funcion
envuelta, persiste el evento via el caso de uso inyectado
(`AUDITORIA_SERVICE` en config). La capa de api no conoce el ORM: el
escritorio vive en application/infrastructure.
"""

from functools import wraps
from typing import Callable

from flask import current_app, has_request_context, request

ACTIONS_SENSIBLES: dict[Callable, str] = {}


def auditar(accion: str):
    def decorator(fn):
        ACTIONS_SENSIBLES[fn] = accion

        @wraps(fn)
        def wrapper(*args, **kwargs):
            resultado = fn(*args, **kwargs)
            _registrar(accion)
            return resultado

        return wrapper

    return decorator


def _registrar(accion: str) -> None:
    """Persiste el evento de auditoria despues de ejecutar la accion."""
    if not has_request_context():
        return
    servicio = current_app.config.get("AUDITORIA_SERVICE")
    if servicio is None:
        return
    usuario_id = request.headers.get("X-User-Id")
    ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "")[:45]
    servicio.registrar(
        accion,
        entidad_tipo=accion,
        entidad_id=None,
        usuario_id=usuario_id,
        detalle=None,
        ip=ip,
    )
