"""Auditoría de acciones sensibles (RNF-06).

Decorador para endpoints cuyas acciones deben quedar registradas
(en LogAuditoria). Ej: crear pedido, procesar pago, aprobar cotización.
"""

from functools import wraps
from typing import Callable

ACTIONS_SENSIBLES: dict[Callable, str] = {}


def auditar(accion: str):
    def decorator(fn):
        ACTIONS_SENSIBLES[fn] = accion
        return fn

    return decorator