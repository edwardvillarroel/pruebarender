"""Datos de facturación que llegan del checkout.

El checkout guarda en `pedidos.direccion_envio` un JSON con los datos del
cliente que el usuario cautó: tipo de documento, RUT, razón social, giro,
dirección y comuna. Este módulo normaliza y valida eso, y decide qué es
exigible según el tipo de documento.

Es el punto donde se traduce el "formulario" a los datos que el SII exige:
- **Boleta (DTE 39)**: basta el RUT del receptor.
- **Factura (DTE 33)**: además del RUT son obligatorios razón social, giro,
  dirección y comuna.
"""

from __future__ import annotations

from app.domain.entities.documento_tributario import DatosFacturacion
from app.domain.enums import TipoDocumentoTributario

RUT_CONSUMIDOR_FINAL = "66666666-6"

_TIPOS_VALIDOS = {
    "boleta": TipoDocumentoTributario.BOLETA,
    "factura": TipoDocumentoTributario.FACTURA,
}


def normalizar_rut(valor) -> str:
    """Deja el RUT en el formato del SII: `12345678-5`.

    Acepta lo que mande el formulario (`12.345.678-5`, `123456785`, con o sin
    puntos) y devuelve siempre el cuerpo con el dígito verificador separado
    por un guion. Es el mismo criterio del frontend
    (`validacionescheckout.js`), para que el backend no rechace un RUT que el
    checkout ya dio por bueno.
    """
    limpio = "".join(
        caracter
        for caracter in str(valor or "")
        if caracter.isdigit() or caracter.lower() == "k"
    ).upper()[:9]
    if len(limpio) < 2:
        return limpio
    return f"{limpio[:-1]}-{limpio[-1]}"


def es_rut_valido(rut: str) -> bool:
    """Valida el dígito verificador del RUT.

    El consumidor final (`66666666-6`) es el RUT que el SII acepta para quien
    no tiene RUT: no pasa el algoritmo de verificación, pero sí es válido.
    """
    if not rut:
        return False
    if rut == RUT_CONSUMIDOR_FINAL:
        return True
    cuerpo, _, verificador = rut.rpartition("-")
    if not cuerpo or not verificador:
        return False
    if not cuerpo.isdigit() or len(cuerpo) not in (7, 8):
        return False
    return _digito_verificador(cuerpo) == verificador


def _digito_verificador(cuerpo: str) -> str:
    """Dígito verificador del RUT (mismo algoritmo que el frontend).

    Los pesos son 2, 3, 4, 5, 6, 7 y vuelven a 2, de derecha a izquierda.
    """
    factor = 2
    suma = 0
    for digito in reversed(cuerpo):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - (suma % 11)
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


def tipo_documento_de(valor) -> TipoDocumentoTributario | None:
    """Traduce `'boleta'` / `'factura'` al enum del dominio."""
    return _TIPOS_VALIDOS.get(str(valor or "").strip().lower())


def extraer_datos_facturacion(
    cliente: dict | None, tipo: TipoDocumentoTributario | None = None
) -> DatosFacturacion | None:
    """Datos del receptor desde el JSON del checkout.

    Devuelve `None` si no hay tipo de documento o el RUT no es válido: sin
    receptor no hay documento que emitir. Los datos que sí son obligatorios
    (razón social, giro, dirección y comuna de una factura) NO se validan acá:
    eso lo hace el caso de uso, que decide si el documento se emite o no.
    """
    if not cliente:
        return None
    tipo_documento = tipo or tipo_documento_de(cliente.get("tipoDocumento"))
    if tipo_documento is None:
        return None
    rut = normalizar_rut(cliente.get("rut"))
    if not es_rut_valido(rut):
        return None

    return DatosFacturacion(
        tipo=tipo_documento,
        rut=rut,
        razon_social=_texto(cliente.get("razonSocial")),
        giro=_texto(cliente.get("giro")),
        direccion=_direccion(cliente),
        comuna=_texto(cliente.get("comuna")),
        email=_texto(cliente.get("email")),
    )


def _texto(valor) -> str | None:
    texto = str(valor or "").strip()
    return texto or None


def _direccion(cliente: dict) -> str | None:
    partes = [
        _texto(cliente.get("direccion")),
        _texto(cliente.get("numero")),
        _texto(cliente.get("dpto")),
    ]
    direccion = " ".join(parte for parte in partes if parte)
    return direccion or None
