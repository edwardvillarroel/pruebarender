


from __future__ import annotations

from app.domain.entities.documento_tributario import DatosFacturacion
from app.domain.enums import TipoDocumentoTributario

RUT_CONSUMIDOR_FINAL = "66666666-6"

_TIPOS_VALIDOS = {
    "boleta": TipoDocumentoTributario.BOLETA,
    "factura": TipoDocumentoTributario.FACTURA,
}


def normalizar_rut(valor) -> str:

    limpio = "".join(
        caracter
        for caracter in str(valor or "")
        if caracter.isdigit() or caracter.lower() == "k"
    ).upper()[:9]
    if len(limpio) < 2:
        return limpio
    return f"{limpio[:-1]}-{limpio[-1]}"


def es_rut_valido(rut: str) -> bool:

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
    return _TIPOS_VALIDOS.get(str(valor or "").strip().lower())


def extraer_datos_facturacion(
    cliente: dict | None, tipo: TipoDocumentoTributario | None = None
) -> DatosFacturacion | None:

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
