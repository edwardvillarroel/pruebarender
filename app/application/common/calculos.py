ENVIO_GRATIS_DESDE = 50000

def calcular_envio(subtotal: int, entrega: str | None) -> int:
    return 0
 

def calcular_total_con_envio(subtotal: int, entrega: str | None) -> int:
    return int(subtotal) + calcular_envio(subtotal, entrega)