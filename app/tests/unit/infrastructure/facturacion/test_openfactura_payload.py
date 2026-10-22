"""El payload que se manda al proveedor tiene que estar EXACTO.

Los dos formatos de documento (boleta 39 y factura 33) tienen esquemas
distintos y el proveedor los valida con su propio XSD antes de mandarlos al
SII: un campo de más o de menos y el documento se rechaza.

Estos tests son la transcripción de las reglas del API:

- **Boleta (39)**: las líneas van con el precio BRUTO, no lleva `TasaIVA`, el
  medio de pago se llama `MedioPago` y el emisor lleva `CdgSIISucur` (que en
  la factura no puede).
- **Factura (33)**: las líneas van con el precio NETO, lleva `TasaIVA`, el
  medio de pago se llama `FmaPago`, el emisor lleva `Acteco` y el receptor
  tiene que declarar razón social, giro, dirección y comuna.

Se prueban con un transporte HTTP falso: no sale nada a la red.
"""

from __future__ import annotations

import base64
import json
from datetime import date

import httpx
import pytest

from app.domain.enums import MedioPagoFacturacion, TipoDocumentoTributario
from app.domain.entities.documento_tributario import DatosFacturacion, LineaDocumento
from app.domain.interfaces.facturacion import (
    ErrorEmisionTributaria,
    SolicitudDocumentoTributario,
)
from app.infrastructure.facturacion.openfactura_cliente import OpenFacturaCliente

CONFIG = {
    "OPENFACTURA_API_KEY": "clave-de-prueba",
    "OPENFACTURA_API_URL": "https://dev-api.haulmer.com",
    "EMISOR_RUT": "76795561-8",
    "EMISOR_RAZON_SOCIAL": "HAULMER CHILE SPA",
    "EMISOR_GIRO": "PRODUCTOS Y SERVICIOS",
    "EMISOR_DIRECCION": "A PRAT 545 DP 2",
    "EMISOR_COMUNA": "Curicó",
    "EMISOR_ACTIVIDAD_ECONOMICA": "641990",
    "EMISOR_CDG_SII_SUCUR": "81303347",
}


def _solicitud(tipo, total=1000, lineas=None) -> SolicitudDocumentoTributario:
    return SolicitudDocumentoTributario(
        tipo=tipo,
        clave_idempotencia="dte-123",
        receptor=DatosFacturacion(
            tipo=tipo,
            rut="12345678-5",
            razon_social="CLIENTE LTDA",
            giro="COMERCIO",
            direccion="AV. ALTA 123",
            comuna="Providencia",
        ),
        lineas=lineas
        or [LineaDocumento(nombre="Llavero 3D", cantidad=1, precio_unitario=total)],
        monto_total=total,
        medio_pago=MedioPagoFacturacion.TARJETA,
        fecha_emision=date(2026, 10, 22),
    )


def _cliente(handler) -> OpenFacturaCliente:
    return OpenFacturaCliente(CONFIG, transporte=httpx.MockTransport(handler))


def _capturado(handler):
    """Devuelve (respuesta, cuerpo enviado, headers)."""
    capturado = {}

    def _envuelto(peticion: httpx.Request) -> httpx.Response:
        capturado["cuerpo"] = json.loads(peticion.content.decode("utf-8"))
        capturado["headers"] = dict(peticion.headers)
        capturado["url"] = str(peticion.url)
        return handler(peticion)

    return _envuelto, capturado


def _respuesta_exitosa():
    return httpx.Response(
        200,
        json={
            "TOKEN": "a" * 64,
            "FOLIO": 712500,
            "RESOLUCION": {"fecha": "2026-10-22", "numero": 123},
            "PDF": base64.b64encode(b"%PDF-1.4 de prueba").decode("ascii"),
        },
    )


# --------------------------------------------------------------------------
# La boleta (DTE 39)
# --------------------------------------------------------------------------


def test_la_boleta_va_con_precios_brutos_y_sin_tasa_de_iva():
    _, capturado = _capturado(lambda p: _respuesta_exitosa())
    cliente = _cliente(_)

    cliente.emitir(_solicitud(TipoDocumentoTributario.BOLETA, total=1000))

    encabezado = capturado["cuerpo"]["dte"]["Encabezado"]
    assert encabezado["IdDoc"]["TipoDTE"] == 39
    assert "TasaIVA" not in encabezado["Totales"]
    assert encabezado["Totales"] == {
        "MntNeto": 840,
        "IVA": 160,
        "MntTotal": 1000,
        "VlrPagar": 1000,
    }
    detalle = capturado["cuerpo"]["dte"]["Detalle"][0]
    assert detalle["PrcItem"] == 1000
    assert detalle["MontoItem"] == 1000


def test_la_boleta_usa_medio_pago_e_ind_servicio():
    _, capturado = _capturado(lambda p: _respuesta_exitosa())
    cliente = _cliente(_)

    cliente.emitir(_solicitud(TipoDocumentoTributario.BOLETA))

    id_doc = capturado["cuerpo"]["dte"]["Encabezado"]["IdDoc"]
    assert id_doc["MedioPago"] == 2  # tarjeta
    assert "FmaPago" not in id_doc
    assert id_doc["IndServicio"] == 3  # venta de bienes
    assert id_doc["FchEmis"] == "2026-10-22"
    assert id_doc["Folio"] == 0  # lo asigna el proveedor


def test_la_boleta_no_manda_actividad_economica():
    """`Acteco` es de la factura: en la boleta el proveedor lo rechaza."""
    _, capturado = _capturado(lambda p: _respuesta_exitosa())
    cliente = _cliente(_)

    cliente.emitir(_solicitud(TipoDocumentoTributario.BOLETA))

    emisor = capturado["cuerpo"]["dte"]["Encabezado"]["Emisor"]
    assert "Acteco" not in emisor
    assert emisor["CdgSIISucur"] == "81303347"


# --------------------------------------------------------------------------
# La factura (DTE 33)
# --------------------------------------------------------------------------


def test_la_factura_va_con_precios_netos_y_tasa_de_iva():
    _, capturado = _capturado(lambda p: _respuesta_exitosa())
    cliente = _cliente(_)

    cliente.emitir(_solicitud(TipoDocumentoTributario.FACTURA, total=1000))

    encabezado = capturado["cuerpo"]["dte"]["Encabezado"]
    assert encabezado["IdDoc"]["TipoDTE"] == 33
    assert encabezado["Totales"]["TasaIVA"] == "19"
    assert encabezado["Totales"]["MntNeto"] == 840
    assert encabezado["Totales"]["IVA"] == 160
    assert encabezado["Totales"]["MntTotal"] == 1000
    detalle = capturado["cuerpo"]["dte"]["Detalle"][0]
    assert detalle["PrcItem"] == 840
    assert detalle["MontoItem"] == 840


def test_la_factura_usa_fma_pago_y_no_medio_pago():
    _, capturado = _capturado(lambda p: _respuesta_exitosa())
    cliente = _cliente(_)

    cliente.emitir(_solicitud(TipoDocumentoTributario.FACTURA))

    id_doc = capturado["cuerpo"]["dte"]["Encabezado"]["IdDoc"]
    assert id_doc["FmaPago"] == 2
    assert "MedioPago" not in id_doc
    assert id_doc["TpoTranVenta"] == 1


def test_la_factura_manda_actividad_economica_y_no_el_codigo_de_sucursal():
    _, capturado = _capturado(lambda p: _respuesta_exitosa())
    cliente = _cliente(_)

    cliente.emitir(_solicitud(TipoDocumentoTributario.FACTURA))

    emisor = capturado["cuerpo"]["dte"]["Encabezado"]["Emisor"]
    assert emisor["Acteco"] == "641990"
    assert "CdgSIISucur" not in emisor


def test_la_factura_exige_los_datos_del_receptor():
    _, capturado = _capturado(lambda p: _respuesta_exitosa())
    cliente = _cliente(_)

    cliente.emitir(_solicitud(TipoDocumentoTributario.FACTURA))

    receptor = capturado["cuerpo"]["dte"]["Encabezado"]["Receptor"]
    assert receptor["RUTRecep"] == "12345678-5"
    assert receptor["RznSocRecep"] == "CLIENTE LTDA"
    assert receptor["GiroRecep"] == "COMERCIO"
    assert receptor["DirRecep"] == "AV. ALTA 123"
    assert receptor["CmnaRecep"] == "Providencia"


def test_las_lineas_de_la_factura_suman_el_neto_del_documento():
    """La última línea absorbe el descuadre del redondeo.

    Tres unidades de 60 bruto son 180: el neto unitario es 50 y el del
    documento 151 (180/1.19 = 151.26). La suma de las líneas tiene que dar
    151, no 150.
    """
    _, capturado = _capturado(lambda p: _respuesta_exitosa())
    cliente = _cliente(_)
    lineas = [LineaDocumento(nombre="Llavero 3D", cantidad=3, precio_unitario=60)]

    cliente.emitir(
        _solicitud(TipoDocumentoTributario.FACTURA, total=180, lineas=lineas)
    )

    encabezado = capturado["cuerpo"]["dte"]["Encabezado"]
    detalle = capturado["cuerpo"]["dte"]["Detalle"]
    assert encabezado["Totales"]["MntNeto"] == 151
    assert sum(linea["MontoItem"] for linea in detalle) == 151


# --------------------------------------------------------------------------
# Idempotencia y errores
# --------------------------------------------------------------------------


def test_manda_la_clave_de_idempotencia():
    _, capturado = _capturado(lambda p: _respuesta_exitosa())
    cliente = _cliente(_)

    cliente.emitir(_solicitud(TipoDocumentoTributario.BOLETA))

    assert capturado["headers"]["idempotency-key"] == "dte-123"
    assert capturado["headers"]["apikey"] == "clave-de-prueba"


def test_cuando_el_proveedor_dice_ya_emitido_devuelve_el_token():
    """`OF-06` no es un fallo: el documento existe y hay que recuperarlo.

    El token viene en el detalle del error, y con él se puede bajar el PDF.
    """
    def _handler(peticion):
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": "Este DTE ya fue emitido (Idempotency-Key)",
                    "code": "OF-06",
                    "details": [{"field": "token", "issue": "b" * 64}],
                }
            },
        )

    cliente = _cliente(_handler)

    with pytest.raises(ErrorEmisionTributaria) as excepcion:
        cliente.emitir(_solicitud(TipoDocumentoTributario.BOLETA))

    assert excepcion.value.codigo == "OF-06"
    assert excepcion.value.ya_emitido is True
    assert excepcion.value.token == "b" * 64


def test_un_error_de_validacion_trae_el_codigo_y_el_detalle():
    def _handler(peticion):
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": "Datos inválidos",
                    "code": "OF-01",
                    "details": [{"field": "IVA", "issue": "Monto erróneo : 192/190"}],
                }
            },
        )

    cliente = _cliente(_handler)

    with pytest.raises(ErrorEmisionTributaria) as excepcion:
        cliente.emitir(_solicitud(TipoDocumentoTributario.BOLETA))

    assert excepcion.value.codigo == "OF-01"
    assert excepcion.value.ya_emitido is False
    assert "IVA" in str(excepcion.value)


def test_sin_api_key_no_intenta_emprimir():
    cliente = OpenFacturaCliente({**CONFIG, "OPENFACTURA_API_KEY": ""})
    assert cliente.configurado is False
    with pytest.raises(ErrorEmisionTributaria):
        cliente.emitir(_solicitud(TipoDocumentoTributario.BOLETA))


def test_el_documento_emitido_trae_el_folio_y_el_pdf():
    cliente = _cliente(lambda p: _respuesta_exitosa())

    emitido = cliente.emitir(_solicitud(TipoDocumentoTributario.BOLETA, total=1000))

    assert emitido.folio == 712500
    assert emitido.token == "a" * 64
    assert emitido.monto_neto == 840
    assert emitido.iva == 160
    assert emitido.monto_total == 1000
    assert emitido.pdf == b"%PDF-1.4 de prueba"


def test_consultar_el_documento_devuelve_el_folio_y_el_pdf():
    def _handler(peticion):
        return httpx.Response(
            200,
            json={
                "pdf": base64.b64encode(b"%PDF-1.4").decode("ascii"),
                "folio": 712500,
            },
        )

    cliente = _cliente(_handler)

    consultado = cliente.consultar_documento("c" * 64)

    assert consultado.folio == 712500
    assert consultado.pdf == b"%PDF-1.4"
