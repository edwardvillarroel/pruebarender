"""Emisión del documento electrónico (boleta o factura) de un pedido.

Es el caso de uso que conoce el ciclo de vida del documento: reserva la fila,
llama al proveedor con una clave de idempotencia determinista, guarda el folio
y el PDF, y sabe recuperar un documento que el proveedor ya había emitido.

La emisión NUNCA debe romper el pago: si el proveedor falla, el error queda
registrado en la fila del documento y el pago sigue su curso. Por eso el
llamador (`ProcesarPago`) captura la excepción.
"""

from __future__ import annotations

import json
import logging
from uuid import UUID

from app.application.common.calculos import calcular_envio
from app.application.common.facturacion import (
    extraer_datos_facturacion,
    tipo_documento_de,
)
from app.domain.entities.documento_tributario import (
    DocumentoTributario,
    LineaDocumento,
)
from app.domain.entities.pedido import Pedido
from app.domain.enums import (
    EstadoDocumentoTributario,
    MedioPagoFacturacion,
    TipoDocumentoTributario,
)
from app.domain.facturacion import calcular_montos
from app.domain.interfaces.facturacion import (
    DocumentoEmitido,
    EmisorTributario,
    ErrorEmisionTributaria,
    ServicioDocumentacionTributaria,
    SolicitudDocumentoTributario,
)
from app.domain.interfaces.repositories import (
    DocumentoTributarioRepository,
    PedidoRepository,
)
from app.domain.time import hoy_chile

logger = logging.getLogger(__name__)

PREFIJO_CLAVE = "dte-"
NOMBRE_ENVIO = "Envío"


class EmitirDocumentoTributario(ServicioDocumentacionTributaria):
    def __init__(
        self,
        pedidos: PedidoRepository,
        documentos: DocumentoTributarioRepository,
        emisor: EmisorTributario,
    ) -> None:
        self._pedidos = pedidos
        self._documentos = documentos
        self._emisor = emisor

    def emitir_para_pedido(self, pedido_id: UUID) -> DocumentoTributario | None:
        pedido = self._pedidos.get_by_id(pedido_id)
        if pedido is None:
            logger.warning("No se puede emitir el documento: el pedido %s no existe", pedido_id)
            return None

        cliente = _cliente_de(pedido)
        tipo = pedido.tipo_documento or tipo_documento_de(cliente.get("tipoDocumento"))
        datos = extraer_datos_facturacion(cliente, tipo)
        if datos is None:
            logger.info(
                "El pedido %s no pide documento tributario: sin RUT o sin tipo", pedido_id
            )
            return None

        faltante = _datos_faltantes(datos)
        if faltante:
            raise ErrorEmisionTributaria(
                "El pedido no tiene los datos que exige la factura: " + ", ".join(faltante)
            )

        clave = f"{PREFIJO_CLAVE}{pedido_id}"
        documento = self._documentos.get_by_clave_idempotencia(clave)
        if documento is not None and documento.estado is EstadoDocumentoTributario.EMITIDO:
            logger.info(
                "El pedido %s ya tiene documento emitido (folio %s)", pedido_id, documento.folio
            )
            return documento

        if documento is None:
            documento = DocumentoTributario(
                tipo=datos.tipo,
                clave_idempotencia=clave,
                rut_emisor=self._emisor.rut_emisor,
                rut_receptor=datos.rut,
                pedido_id=pedido_id,
            )
            self._documentos.add(documento)

        lineas = _lineas_del_pedido(pedido)
        solicitud = SolicitudDocumentoTributario(
            tipo=datos.tipo,
            clave_idempotencia=clave,
            receptor=datos,
            lineas=lineas,
            monto_total=pedido.total,
            medio_pago=MedioPagoFacturacion.TARJETA,
            fecha_emision=hoy_chile(),
        )

        try:
            emitido = self._emisor.emitir(solicitud)
        except ErrorEmisionTributaria as exc:
            if exc.ya_emitido and exc.token:
                # El proveedor ya lo había emitido: se recupera en vez de fallar.
                logger.info(
                    "El documento del pedido %s ya estaba emitido; se recupera el token %s",
                    pedido_id,
                    exc.token,
                )
                emitido = self._recuperar(exc.token, pedido.total)
            else:
                documento.estado = EstadoDocumentoTributario.ERROR
                documento.error = f"{exc.codigo or ''}: {exc}".strip(": ")
                self._documentos.update(documento)
                raise

        documento.estado = EstadoDocumentoTributario.EMITIDO
        documento.folio = emitido.folio
        documento.token = emitido.token
        documento.monto_neto = emitido.monto_neto
        documento.iva = emitido.iva
        documento.monto_total = emitido.monto_total
        documento.fecha_emision = emitido.fecha_emision
        documento.razon_social_receptor = datos.razon_social
        documento.giro_receptor = datos.giro
        documento.direccion_receptor = datos.direccion
        documento.comuna_receptor = datos.comuna
        documento.error = None
        if emitido.pdf:
            documento.pdf = emitido.pdf
        self._documentos.update(documento)

        logger.info(
            "Documento emitido para el pedido %s: folio %s token %s",
            pedido_id,
            emitido.folio,
            emitido.token,
        )
        return documento

    def _recuperar(self, token: str, monto_total: int) -> DocumentoEmitido:
        """Reconstruye el documento emitido a partir de su token."""
        consultado = self._emisor.consultar_documento(token)
        neto, iva = calcular_montos(monto_total)
        return DocumentoEmitido(
            folio=consultado.folio,
            token=token,
            monto_neto=neto,
            iva=iva,
            monto_total=monto_total,
            fecha_emision=hoy_chile(),
            pdf=consultado.pdf,
        )


def _datos_faltantes(datos) -> list[str]:
    """Datos que el SII exige y que no llegaron."""
    if datos.tipo is not TipoDocumentoTributario.FACTURA:
        return []
    faltantes = []
    if not datos.razon_social:
        faltantes.append("razón social")
    if not datos.giro:
        faltantes.append("giro")
    if not datos.direccion:
        faltantes.append("dirección")
    if not datos.comuna:
        faltantes.append("comuna")
    return faltantes


def _cliente_de(pedido: Pedido) -> dict:
    """El JSON con los datos del cliente que guardó el checkout."""
    if not pedido.direccion_envio:
        return {}
    try:
        datos = json.loads(pedido.direccion_envio)
    except (TypeError, ValueError):
        return {}
    return datos if isinstance(datos, dict) else {}


def _lineas_del_pedido(pedido: Pedido) -> list[LineaDocumento]:
    """Líneas del documento: los productos del pedido y, si corresponde, el envío.

    Las líneas tienen que sumar el total cobrado, así que el costo de envío
    va como una línea más cuando se cobra.
    """
    lineas = [
        LineaDocumento(
            nombre=detalle.nombre or "Producto",
            cantidad=detalle.cantidad,
            precio_unitario=detalle.precio_unitario,
        )
        for detalle in pedido.detalles
    ]
    subtotal = sum(linea.monto_bruto for linea in lineas)
    envio = calcular_envio(subtotal, pedido.entrega)
    if envio > 0:
        lineas.append(
            LineaDocumento(nombre=NOMBRE_ENVIO, cantidad=1, precio_unitario=envio)
        )
    return lineas
