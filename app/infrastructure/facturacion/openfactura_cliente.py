






from __future__ import annotations

import base64
import logging
from dataclasses import dataclass

import httpx

from app.domain.enums import TipoDocumentoTributario
from app.domain.facturacion import (
    TASA_IVA,
    ajustar_ultima_linea,
    calcular_montos,
    netos_unitarios,
)
from app.domain.interfaces.facturacion import (
    DocumentoConsultado,
    DocumentoEmitido,
    EmisorTributario,
    ErrorEmisionTributaria,
    SolicitudDocumentoTributario,
)

logger = logging.getLogger(__name__)


@dataclass
class DatosEmisor:


    rut: str
    razon_social: str
    giro: str
    direccion: str
    comuna: str
    actividad_economica: str
    codigo_sucursal: str


class OpenFacturaCliente(EmisorTributario):

    def __init__(
        self, config: dict, transporte: httpx.BaseTransport | None = None
    ) -> None:
        self._api_key = str(config.get("OPENFACTURA_API_KEY") or "").strip()
        self._base_url = str(
            config.get("OPENFACTURA_API_URL") or "https://api.haulmer.com"
        ).rstrip("/")
        self._timeout = float(config.get("OPENFACTURA_TIMEOUT") or 30)
        self._transporte = transporte
        self._emisor = DatosEmisor(
            rut=str(config.get("EMISOR_RUT") or "").strip(),
            razon_social=str(config.get("EMISOR_RAZON_SOCIAL") or "").strip(),
            giro=str(config.get("EMISOR_GIRO") or "").strip(),
            direccion=str(config.get("EMISOR_DIRECCION") or "").strip(),
            comuna=str(config.get("EMISOR_COMUNA") or "").strip(),
            actividad_economica=str(
                config.get("EMISOR_ACTIVIDAD_ECONOMICA") or ""
            ).strip(),
            codigo_sucursal=str(config.get("EMISOR_CDG_SII_SUCUR") or "").strip(),
        )

    @property
    def configurado(self) -> bool:
        return bool(self._api_key) and bool(self._emisor.rut)

    @property
    def rut_emisor(self) -> str:
        return self._emisor.rut

    def emitir(self, solicitud: SolicitudDocumentoTributario) -> DocumentoEmitido:
        if not self.configurado:
            raise ErrorEmisionTributaria(
                "OpenFactura no está configurado (falta OPENFACTURA_API_KEY o "
                "EMISOR_RUT)"
            )

        payload = self._construir_payload(solicitud)
        cuerpo = self._post("/v2/dte/document", payload, solicitud.clave_idempotencia)

        folio = cuerpo.get("FOLIO")
        token = cuerpo.get("TOKEN")
        if folio is None or not token:
            raise ErrorEmisionTributaria(
                "El proveedor respondió sin folio ni token",
                codigo=cuerpo.get("codigo"),
            )

        neto, iva = calcular_montos(solicitud.monto_total)
        return DocumentoEmitido(
            folio=int(folio),
            token=str(token),
            monto_neto=neto,
            iva=iva,
            monto_total=solicitud.monto_total,
            fecha_emision=solicitud.fecha_emision,
            pdf=_decodificar_pdf(cuerpo.get("PDF")),
        )

    def consultar_documento(self, token: str) -> DocumentoConsultado:
        cuerpo = self._get(f"/v2/dte/document/{token}/pdf")
        pdf = cuerpo.get("pdf")
        folio = cuerpo.get("folio")
        if not folio:
            raise ErrorEmisionTributaria(
                "El proveedor no devolvió el folio del documento", codigo="SIN_FOLIO"
            )
        return DocumentoConsultado(
            folio=int(folio), pdf=_decodificar_pdf(pdf) if pdf else None
        )


    def _construir_payload(
        self, solicitud: SolicitudDocumentoTributario
    ) -> dict:
        if solicitud.tipo is TipoDocumentoTributario.FACTURA:
            return self._payload_factura(solicitud)
        return self._payload_boleta(solicitud)

    def _payload_boleta(self, solicitud: SolicitudDocumentoTributario) -> dict:

        neto, iva = calcular_montos(solicitud.monto_total)
        emisor = self._emisor
        receptor: dict = {"RUTRecep": solicitud.receptor.rut}
        if solicitud.receptor.direccion:
            receptor["DirRecep"] = solicitud.receptor.direccion
        if solicitud.receptor.comuna:
            receptor["CmnaRecep"] = solicitud.receptor.comuna
        if solicitud.receptor.razon_social:
            receptor["RznSocRecep"] = solicitud.receptor.razon_social

        return {
            "response": ["XML", "PDF", "FOLIO", "TIMBRE", "RESOLUCION"],
            "dte": {
                "Encabezado": {
                    "IdDoc": {
                        "TipoDTE": solicitud.tipo.codigo_dte,
                        "Folio": 0,
                        "FchEmis": solicitud.fecha_emision.isoformat(),
                        "IndServicio": 3,
                        "MedioPago": int(solicitud.medio_pago),
                    },
                    "Emisor": {
                        "RUTEmisor": emisor.rut,
                        "RznSocEmisor": emisor.razon_social,
                        "GiroEmisor": emisor.giro,
                        "DirOrigen": emisor.direccion,
                        "CmnaOrigen": emisor.comuna,
                        "CdgSIISucur": emisor.codigo_sucursal,
                    },
                    "Receptor": receptor,
                    "Totales": {
                        "MntNeto": neto,
                        "IVA": iva,
                        "MntTotal": solicitud.monto_total,
                        "VlrPagar": solicitud.monto_total,
                    },
                },
                "Detalle": [
                    {
                        "NroLinDet": numero,
                        "NmbItem": linea.nombre,
                        "QtyItem": linea.cantidad,
                        "PrcItem": linea.precio_unitario,
                        "MontoItem": linea.monto_bruto,
                    }
                    for numero, linea in enumerate(solicitud.lineas, start=1)
                ],
            },
        }

    def _payload_factura(self, solicitud: SolicitudDocumentoTributario) -> dict:

        neto, iva = calcular_montos(solicitud.monto_total)
        emisor = self._emisor
        receptor = {
            "RUTRecep": solicitud.receptor.rut,
            "RznSocRecep": solicitud.receptor.razon_social or "",
            "GiroRecep": solicitud.receptor.giro or "",
            "DirRecep": solicitud.receptor.direccion or "",
            "CmnaRecep": solicitud.receptor.comuna or "",
        }

        precios_netos = netos_unitarios(
            [linea.precio_unitario for linea in solicitud.lineas]
        )
        montos_netos = [
            precios_netos[indice] * linea.cantidad
            for indice, linea in enumerate(solicitud.lineas)
        ]
        montos_netos = ajustar_ultima_linea(montos_netos, neto)

        detalle = []
        for numero, (linea, precio_neto, monto_neto) in enumerate(
            zip(solicitud.lineas, precios_netos, montos_netos), start=1
        ):
            cantidad = linea.cantidad or 1
            if cantidad > 1 and monto_neto != precio_neto * cantidad:
                precio_unitario = precio_neto
            else:
                precio_unitario = monto_neto // cantidad
            detalle.append(
                {
                    "NroLinDet": numero,
                    "NmbItem": linea.nombre,
                    "QtyItem": cantidad,
                    "PrcItem": precio_unitario,
                    "MontoItem": monto_neto,
                }
            )

        return {
            "response": ["XML", "PDF", "FOLIO", "TIMBRE", "RESOLUCION"],
            "dte": {
                "Encabezado": {
                    "IdDoc": {
                        "TipoDTE": solicitud.tipo.codigo_dte,
                        "Folio": 0,
                        "FchEmis": solicitud.fecha_emision.isoformat(),
                        "TpoTranVenta": 1,
                        "FmaPago": int(solicitud.medio_pago),
                    },
                    "Emisor": {
                        "RUTEmisor": emisor.rut,
                        "RznSoc": emisor.razon_social,
                        "GiroEmis": emisor.giro,
                        "Acteco": emisor.actividad_economica,
                        "DirOrigen": emisor.direccion,
                        "CmnaOrigen": emisor.comuna,
                    },
                    "Receptor": receptor,
                    "Totales": {
                        "MntNeto": neto,
                        "TasaIVA": str(TASA_IVA),
                        "IVA": iva,
                        "MntTotal": solicitud.monto_total,
                        "VlrPagar": solicitud.monto_total,
                    },
                },
                "Detalle": detalle,
            },
        }


    def _post(self, ruta: str, payload: dict, idempotency_key: str) -> dict:
        try:
            with self._cliente_http() as cliente:
                respuesta = cliente.post(
                    ruta, json=payload, headers={"Idempotency-Key": idempotency_key}
                )
        except httpx.HTTPError as exc:
            raise ErrorEmisionTributaria(
                f"No se pudo emitir el documento: {exc}"
            ) from exc
        return self._cuerpo(respuesta)

    def _get(self, ruta: str) -> dict:
        try:
            with self._cliente_http() as cliente:
                respuesta = cliente.get(ruta)
        except httpx.HTTPError as exc:
            raise ErrorEmisionTributaria(
                f"No se pudo consultar el documento: {exc}"
            ) from exc
        return self._cuerpo(respuesta)

    def _cliente_http(self) -> httpx.Client:
        return httpx.Client(
            base_url=self._base_url,
            headers={"apikey": self._api_key},
            timeout=self._timeout,
            transport=self._transporte,
        )

    def _cuerpo(self, respuesta: httpx.Response) -> dict:
        if respuesta.status_code == 200:
            try:
                return respuesta.json()
            except ValueError as exc:
                raise ErrorEmisionTributaria(
                    "El proveedor respondió un cuerpo que no es JSON"
                ) from exc
        raise self._error(respuesta)

    def _error(self, respuesta: httpx.Response) -> ErrorEmisionTributaria:
        codigo = None
        mensaje = f"El proveedor rechazó el documento (HTTP {respuesta.status_code})"
        token = None
        ya_emitido = False
        try:
            error = respuesta.json().get("error") or {}
        except ValueError:
            error = {}
        codigo = error.get("code")
        if error.get("message"):
            mensaje = str(error["message"])
        detalles = error.get("details") or []
        if codigo == "OF-06":
            ya_emitido = True
            token = _token_de_detalles(detalles)
            if token:
                mensaje = "El documento ya había sido emitido con esa clave"
        elif detalles:
            mensajes = "; ".join(
                f"{detalle.get('field')}: {detalle.get('issue')}"
                for detalle in detalles
                if isinstance(detalle, dict)
            )
            if mensajes:
                mensaje = f"{mensaje} ({mensajes})"
        logger.warning(
            "OpenFactura rechazo el documento: codigo=%s mensaje=%s", codigo, mensaje
        )
        return ErrorEmisionTributaria(
            mensaje, codigo=codigo, token=token, ya_emitido=ya_emitido
        )


def _token_de_detalles(detalles: list) -> str | None:
    for detalle in detalles:
        if isinstance(detalle, dict) and detalle.get("field") == "token":
            return str(detalle.get("issue") or "").strip() or None
    return None


def _decodificar_pdf(pdf_base64: str | None) -> bytes | None:
    if not pdf_base64:
        return None
    try:
        return base64.b64decode(pdf_base64)
    except (ValueError, TypeError):
        return None
