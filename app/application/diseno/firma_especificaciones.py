

from __future__ import annotations

from decimal import Decimal


def firma_especificaciones(
    alto,
    ancho,
    largo,
    unidad: str | None,
    cantidad: int | None,
    uso: str | None,
    material: str | None,
    color: str | None,
) -> str:
    return "|".join(
        [
            _numero_firma(alto, 10),
            _numero_firma(ancho, 10),
            _numero_firma(largo, 10),
            str(unidad or "cm").strip() or "cm",
            str(int(cantidad or 1)),
            str((uso or "Decorativo").strip() or "Decorativo"),
            str((material or "").strip()),
            str((color or "Negro").strip() or "Negro"),
        ]
    )


def _numero_firma(valor, defecto=None) -> str:
    if valor is None or str(valor).strip() == "":
        valor = defecto
    if valor is None or str(valor).strip() == "":
        return ""
    try:
        numero = Decimal(str(valor).strip().replace(",", ".")).normalize()
    except Exception:
        return str(valor).strip()
    if numero == numero.to_integral_value():
        return str(int(numero))
    texto = format(numero, "f")
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return texto or "0"
