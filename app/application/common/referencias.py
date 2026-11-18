

from uuid import UUID

_ALFABETO = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def codificar_referencia(pedido_id: UUID) -> str:
    numero = int.from_bytes(pedido_id.bytes, "big")
    partes: list[str] = []
    while numero:
        numero, resto = divmod(numero, 62)
        partes.append(_ALFABETO[resto])
    return "".join(reversed(partes)) or _ALFABETO[0]


def decodificar_referencia(referencia: str) -> UUID:

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