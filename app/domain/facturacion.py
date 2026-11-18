





from decimal import ROUND_HALF_UP, Decimal

TASA_IVA = 19
FACTOR_IVA = Decimal("1.19")


def redondear(valor) -> int:

    return int(Decimal(valor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calcular_montos(total_bruto: int) -> tuple[int, int]:

    neto = redondear(Decimal(total_bruto) / FACTOR_IVA)
    return neto, total_bruto - neto


def netos_unitarios(precios_brutos: list[int]) -> list[int]:

    return [redondear(Decimal(precio) / FACTOR_IVA) for precio in precios_brutos]


def ajustar_ultima_linea(montos: list[int], total_esperado: int) -> list[int]:

    if not montos:
        return []
    diferencia = total_esperado - sum(montos)
    if diferencia == 0:
        return list(montos)
    ajustados = list(montos)
    ajustados[-1] += diferencia
    return ajustados
