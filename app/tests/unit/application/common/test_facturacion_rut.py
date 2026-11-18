


from __future__ import annotations

import pytest

from app.application.common.facturacion import (
    RUT_CONSUMIDOR_FINAL,
    es_rut_valido,
    extraer_datos_facturacion,
    normalizar_rut,
    tipo_documento_de,
)




@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("12345678-5", "12345678-5"),
        ("12.345.678-5", "12345678-5"),
        ("123456785", "12345678-5"),
        ("12 345 678 5", "12345678-5"),
        ("12345678k", "12345678-K"),
        ("", ""),
        (None, ""),
    ],
)
def test_normaliza_al_formato_del_sii(entrada, esperado):
    assert normalizar_rut(entrada) == esperado




@pytest.mark.parametrize(
    "rut",
    [
        "12345678-5",
        "1234567-4",
        "76795561-8",
        "78064166-5",
        "11111111-1",
        RUT_CONSUMIDOR_FINAL,
    ],
)
def test_acepta_ruts_validos(rut):
    assert es_rut_valido(rut) is True


@pytest.mark.parametrize(
    "rut",
    [
        "12345678-9",
        "1234567-9",
        "123456-9",
        "123456789-9",
        "12345678",
        "abc-def",
        "",
        None,
    ],
)
def test_rechaza_ruts_invalidos(rut):
    assert es_rut_valido(rut) is False


def test_el_consumidor_final_no_pasa_el_digito_verificador_pero_es_valido():
    assert es_rut_valido(RUT_CONSUMIDOR_FINAL) is True
    assert es_rut_valido("66666666-6") and not es_rut_valido("66666666-5")




def test_tipo_documento_acepta_boleta_y_factura():
    from app.domain.enums import TipoDocumentoTributario

    assert tipo_documento_de("boleta") is TipoDocumentoTributario.BOLETA
    assert tipo_documento_de("FACTURA") is TipoDocumentoTributario.FACTURA
    assert tipo_documento_de(" Boleta ") is TipoDocumentoTributario.BOLETA


def test_tipo_documento_rechaza_lo_que_no_sea():
    assert tipo_documento_de("guia") is None
    assert tipo_documento_de("") is None
    assert tipo_documento_de(None) is None




def test_extrae_los_datos_de_una_boleta():
    datos = extraer_datos_facturacion(
        {
            "tipoDocumento": "boleta",
            "rut": "12.345.678-5",
            "email": "cliente@correo.cl",
            "direccion": "AV. ALTA 123",
            "numero": "45",
            "dpto": "7",
            "comuna": "Providencia",
        }
    )
    assert datos is not None
    assert datos.rut == "12345678-5"
    assert datos.direccion == "AV. ALTA 123 45 7"
    assert datos.comuna == "Providencia"
    assert datos.email == "cliente@correo.cl"


def test_sin_rut_no_hay_documento():
    assert extraer_datos_facturacion({"tipoDocumento": "boleta"}) is None


def test_con_rut_invalido_no_hay_documento():
    assert (
        extraer_datos_facturacion({"tipoDocumento": "boleta", "rut": "12345678-9"})
        is None
    )


def test_sin_tipo_de_documento_no_hay_documento():
    assert extraer_datos_facturacion({"rut": "12345678-5"}) is None


def test_sin_cliente_no_hay_documento():
    assert extraer_datos_facturacion(None) is None
    assert extraer_datos_facturacion({}) is None


def test_el_tipo_ganado_por_el_pedido_tiene_precedencia():
    from app.domain.enums import TipoDocumentoTributario

    datos = extraer_datos_facturacion(
        {"tipoDocumento": "boleta", "rut": "12345678-5"},
        TipoDocumentoTributario.FACTURA,
    )
    assert datos is not None
    assert datos.tipo is TipoDocumentoTributario.FACTURA
