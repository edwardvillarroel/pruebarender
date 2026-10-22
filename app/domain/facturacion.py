"""Cálculo de los montos de un documento electrónico (IVA incluido).

Vive en `domain` porque es regla fiscal pura: la usan el cliente del
proveedor (`infrastructure`) para armar el payload y el caso de uso de
emisión (`application`) para guardar los montos, y ninguno de los dos depende
del otro.

Los precios del catálogo son BRUTOS (IVA incluido), que es como se cobran. El
SII tiene dos formatos de documento y cada uno espera los montos de otra
forma:

- **Boleta electrónica (DTE 39)**: las líneas van con el precio BRUTO y el
  documento lleva `MntNeto`, `IVA`, `MntTotal` y `VlrPagar`, sin tasa de IVA.
  El SII deriva el neto del total bruto.
- **Factura electrónica (DTE 33)**: las líneas van con el precio NETO y el
  documento además lleva `TasaIVA`.

En los dos casos el IVA se determina **por diferencia**: `IVA = MntTotal -
MntNeto`. Es lo que permite que el total del documento sea EXACTAMENTE el monto
cobrado, que es lo que el comprobante tiene que decir. El descuadre entre ese
IVA y el 19% exacto del neto nunca pasa de un peso, que es la tolerancia que
acepta el proveedor.

El ajuste del redondeo por línea va en la última línea del documento: es el
"factor de redondeo" del SII, que deja el descuadre en la última línea.
"""

from decimal import ROUND_HALF_UP, Decimal

TASA_IVA = 19
FACTOR_IVA = Decimal("1.19")


def redondear(valor) -> int:
    """Redondeo comercial (media hacia arriba) a pesos enteros.

    `Decimal.quantize` con `ROUND_HALF_UP` y no el `round` de Python, que
    redondea al par (banker's rounding): para .5 exactos darían resultados
    distintos y el comprobante tiene que cuadrar al peso.
    """
    return int(Decimal(valor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calcular_montos(total_bruto: int) -> tuple[int, int]:
    """Devuelve `(neto, iva)` del total bruto cobrado.

    El neto es el total sin IVA, redondeado a pesos. El IVA es la diferencia
    con el total cobrado, para que `neto + iva` dé exactamente lo que se
    cobró, sin un peso de descuadre.
    """
    neto = redondear(Decimal(total_bruto) / FACTOR_IVA)
    return neto, total_bruto - neto


def netos_unitarios(precios_brutos: list[int]) -> list[int]:
    """Neto unitario de cada línea (para la factura).

    El precio unitario neto es el bruto sin IVA, redondeado a pesos.
    """
    return [redondear(Decimal(precio) / FACTOR_IVA) for precio in precios_brutos]


def ajustar_ultima_linea(montos: list[int], total_esperado: int) -> list[int]:
    """Ajusta la última línea para que los montos sumen `total_esperado`.

    El descuadre del redondeo por línea se absorbe en la última, que es lo que
    hace el SII con su "factor de redondeo".
    """
    if not montos:
        return []
    diferencia = total_esperado - sum(montos)
    if diferencia == 0:
        return list(montos)
    ajustados = list(montos)
    ajustados[-1] += diferencia
    return ajustados
