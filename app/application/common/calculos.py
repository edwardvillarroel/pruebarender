"""Reglas de cálculo del pedido (precio de envío y total con IVA).

Las reglas replican lo que el frontend ya muestra en `Checkout.jsx`; viven en
`application/common` para que los casos de uso las compartan sin importarse
entre sí.
"""

ENVIO_GRATIS_DESDE = 50000
COSTO_ENVIO_ESTANDAR = 5990


def calcular_envio(subtotal: int, entrega: str | None) -> int:
    """Costo de envío: gratis en retiro o desde $50.000 de subtotal."""
    if entrega == "retiro":
        return 0
    if subtotal >= ENVIO_GRATIS_DESDE:
        return 0
    return COSTO_ENVIO_ESTANDAR


def calcular_total_con_envio_y_iva(subtotal: int, entrega: str | None) -> int:
    """Total final en pesos chilenos: (subtotal + envío) con IVA (19%)."""
    return round((subtotal + calcular_envio(subtotal, entrega)) * 1.19)