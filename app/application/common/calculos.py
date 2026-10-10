ENVIO_GRATIS_DESDE = 50000
COSTO_ENVIO_ESTANDAR = 5990


def calcular_envio(subtotal: int, entrega: str | None) -> int:
    base = int(subtotal)
    if entrega == "retiro":
        return 0
    if base >= ENVIO_GRATIS_DESDE:
        return 0
    return COSTO_ENVIO_ESTANDAR


def calcular_total_con_envio(subtotal: int, entrega: str | None) -> int:
    return int(subtotal) + calcular_envio(subtotal, entrega)