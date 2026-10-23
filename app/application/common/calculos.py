ENVIO_GRATIS_DESDE = 50000

def calcular_envio(subtotal: int, entrega: str | None) -> int:
    """Costo de envío que cobra la tienda: siempre 0 (lo paga el cliente al transportista)."""
    return 0
 

def calcular_total_con_envio(subtotal: int, entrega: str | None) -> int:
    return int(subtotal) + calcular_envio(subtotal, entrega)