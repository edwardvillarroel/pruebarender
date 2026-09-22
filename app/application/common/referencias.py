"""Codificación de la referencia externa de pedidos hacia TUU.

TUU rechaza `x_reference` con más de 24 caracteres; el `pedido.id` (UUID en
string, 36 caracteres con guiones) no sirve. Se codifica el UUID en base62
(máx. 22 caracteres, solo alfanuméricos) y se decodifica en la confirmación
para resolver el pedido original sin agregar columnas.
"""

from uuid import UUID

_ALFABETO = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def codificar_referencia(pedido_id: UUID) -> str:
    """Codifica el UUID del pedido como base62 (string corto y único)."""
    numero = int.from_bytes(pedido_id.bytes, "big")
    partes: list[str] = []
    while numero:
        numero, resto = divmod(numero, 62)
        partes.append(_ALFABETO[resto])
    return "".join(reversed(partes)) or _ALFABETO[0]


def decodificar_referencia(referencia: str) -> UUID:
    """Decodifica la referencia de TUU de vuelta al UUID del pedido.

    Acepta tanto la codificación base62 como el UUID plano (por tolerancia),
    y lanza `ValueError` si la referencia no corresponde a un pedido.
    """
    if not referencia:
        raise ValueError("Referencia vacía")
    try:
        version_plana = _decodificar_base62(referencia)
        return UUID(bytes=version_plana.to_bytes(16, "big"))
    except (ValueError, OverflowError):
        return UUID(referencia)


def _decodificar_base62(referencia: str) -> int:
    numero = 0
    for caracter in referencia:
        numero = numero * 62 + _ALFABETO.index(caracter)
    return numero