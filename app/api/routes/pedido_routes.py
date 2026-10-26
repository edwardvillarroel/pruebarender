from __future__ import annotations

import json
import re
from io import BytesIO
from uuid import UUID

from flask import Blueprint, current_app, jsonify, request, send_file

from app.api.middleware.auth import requiere_sesion, rol_requerido, usuario_actual
from app.application.common.dto import CrearPedidoDTO, IniciarPagoDTO, ItemPedidoDTO
from app.application.facturacion.consultar_documento_tributario import (
    ConsultarDocumentoTributario,
)
from app.application.pedidos_pagos.cambiar_estado_pedido import (
    CambiarEstadoPedido,
    EstadoInvalidoError,
    PedidoDeOtroUsuarioError,
    PedidoNoEncontradoError,
    TransicionInvalidaError,
)
from app.application.pedidos_pagos.crear_pedido import CrearPedido
from app.application.pedidos_pagos.consultar_pedido import ConsultarPedido
from app.application.pedidos_pagos.gestionar_pedido_no_pagado import (
    GestionarPedidoNoPagado,
    PedidoNoModificableError,
    PedidoNoPagadoDeOtroUsuarioError,
    PedidoNoPagadoNoEncontradoError,
)
from app.application.pedidos_pagos.procesar_pago import ProcesarPago
from app.application.pedidos_pagos.notificar_cancelacion import (
    AvisoPedidoNoEncontradoError,
    NotificarCancelacion,
    PedidoSinCancelarError,
)
from app.application.pedidos_pagos.seguimiento_starken import (
    GestionarSeguimientoStarken,
)
from app.domain.interfaces.pasarela_pago import ErrorPasarela

pedido_bp = Blueprint("pedidos", __name__)
_CLAVE_IDEMPOTENCIA = re.compile(r"^[A-Za-z0-9_-]{1,100}$")


def _entero_opcional(valor) -> int | None:
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, int):
        entero = valor
    else:
        try:
            entero = int(str(valor).strip())
        except (TypeError, ValueError):
            return None
    return entero if entero > 0 else None


def _clave_idempotencia(valor) -> str | None:
    if not isinstance(valor, str):
        return None
    clave = valor.strip()
    return clave if _CLAVE_IDEMPOTENCIA.match(clave) else None


def _servicio_pedido() -> CrearPedido:
    return current_app.config["PEDIDO_SERVICE"]


def _servicio_consulta() -> ConsultarPedido:
    return current_app.config["CONSULTA_PEDIDO_SERVICE"]


def _servicio_pago() -> ProcesarPago:
    return current_app.config["PAGO_SERVICE"]


def _servicio_seguimiento() -> GestionarSeguimientoStarken:
    return current_app.config["SEGUIMIENTO_STARKEN_SERVICE"]


def _servicio_pedido_no_pagado() -> GestionarPedidoNoPagado:
    return current_app.config["PEDIDO_NO_PAGADO_SERVICE"]


def _servicio_cambiar_estado() -> CambiarEstadoPedido:
    return current_app.config["CAMBIAR_ESTADO_PEDIDO_SERVICE"]


def _servicio_notificar_cancelacion() -> NotificarCancelacion:
    return current_app.config["NOTIFICAR_CANCELACION_SERVICE"]


def _servicio_documento() -> ConsultarDocumentoTributario:
    return current_app.config["CONSULTA_DOCUMENTO_SERVICE"]


def _error(msg: str, estado: int):
    return jsonify(mensaje=msg), estado


def _usuario_uuid() -> UUID:
    return UUID(str(usuario_actual()))


def _items(datos: dict) -> list[ItemPedidoDTO]:
    items: list[ItemPedidoDTO] = []
    for raw in datos.get("items") or []:
        if not isinstance(raw, dict) or "id" not in raw:
            raise ValueError("Cada ítem requiere «id» (producto) y «cantidad»")
        try:
            producto_id = UUID(str(raw["id"]))
            cantidad = int(raw.get("cantidad", 1))
        except (TypeError, ValueError):
            raise ValueError("Ítem con id o cantidad inválidos")
        if cantidad < 1:
            raise ValueError("La cantidad debe ser un entero mayor a cero")
        items.append(
            ItemPedidoDTO(
                producto_id=producto_id,
                cantidad=cantidad,
                color=(str(raw["color"]).strip() or None) if raw.get("color") else None,
            )
        )
    return items


def _cliente(pedido) -> dict:
    if not pedido.direccion_envio:
        return {}
    try:
        datos = json.loads(pedido.direccion_envio)
    except (TypeError, ValueError):
        return {}
    return datos if isinstance(datos, dict) else {}


def _a_publico_pedido(pedido, admin: bool = False) -> dict:
    datos = {
        "id": str(pedido.id),
        "estado": pedido.estado.value,
        "total": pedido.total,
        "subtotal": pedido.subtotal,
        "descuento_productos": pedido.descuento_productos,
        "descuento_cupon": pedido.descuento_cupon,
        "cupon_codigo": pedido.cupon_codigo,
        "entrega": pedido.entrega,
        "tipo_documento": (
            pedido.tipo_documento.value if pedido.tipo_documento else None
        ),
        "cliente": _cliente(pedido),
        "fecha": pedido.creado_en.isoformat() if pedido.creado_en else None,
        "codigo_seguimiento": pedido.codigo_seguimiento,
        "transportista": pedido.transportista,
        "estado_seguimiento": pedido.estado_seguimiento,
        "seguimiento_actualizado_en": (
            pedido.seguimiento_actualizado_en.isoformat()
            if pedido.seguimiento_actualizado_en
            else None
        ),
        "items": [
            {
                "producto_id": str(detalle.producto_id),
                "cantidad": detalle.cantidad,
                "precio_unitario": detalle.precio_unitario,
                "precio_original": detalle.precio_original,
                "nombre": detalle.nombre,
                "color": detalle.color,
                "imagen": detalle.imagen,
            }
            for detalle in pedido.detalles
        ],
        "resenas_pendientes": pedido.resenas_pendientes or 0,
        "resenas_completadas": pedido.resenas_completadas or 0,
        "estado_pago": pedido.estado_pago,
        "aviso_cancelacion_en": (
            pedido.aviso_cancelacion_en.isoformat()
            if pedido.aviso_cancelacion_en
            else None
        ),
        "aviso_cancelacion_pendiente": bool(
            pedido.aviso_cancelacion_en and not pedido.aviso_cancelacion_visto
        ),
    }
    if admin:
        datos["usuario_id"] = str(pedido.usuario_id)
    return datos


def _es_dueno(pedido) -> bool:
    if usuario_actual() == str(pedido.usuario_id):
        return True
    return request.headers.get("X-User-Rol") == "admin"


@pedido_bp.post("/pedidos")
@requiere_sesion()
def crear_pedido():
    datos = request.get_json(silent=True) or {}
    try:
        dto = CrearPedidoDTO(
            usuario_id=_usuario_uuid(),
            items=_items(datos),
            entrega=str(datos.get("entrega") or "retiro"),
            cliente=datos.get("cliente"),
        )
    except (ValueError, TypeError) as exc:
        return _error(f"Datos inválidos: {exc}", 400)
    try:
        pedido = _servicio_pedido().ejecutar(dto)
    except ValueError as exc:
        return _error(str(exc), 409)
    return jsonify(_a_publico_pedido(pedido)), 201


@pedido_bp.get("/pedidos")
@requiere_sesion()
def listar_pedidos():
    try:
        usuario_id = _usuario_uuid()
    except (ValueError, TypeError):
        return _error("Sesión inválida", 401)
    pedidos = _servicio_consulta().del_usuario(usuario_id)
    return jsonify(pedidos=[_a_publico_pedido(p) for p in pedidos])


@pedido_bp.get("/pedidos/<uuid:pedido_id>")
@requiere_sesion()
def detalle_pedido(pedido_id: UUID):
    pedido = _servicio_consulta().por_id(pedido_id)
    if pedido is None:
        return _error("Pedido no encontrado", 404)
    if not _es_dueno(pedido):
        return _error("No autorizado", 403)
    return jsonify(_a_publico_pedido(pedido))


@pedido_bp.post("/pedidos/<uuid:pedido_id>/pagar")
@requiere_sesion()
def reintentar_pago(pedido_id: UUID):
    try:
        resultado = _servicio_pedido_no_pagado().reintentar(
            pedido_id, _usuario_uuid()
        )
    except PedidoNoPagadoNoEncontradoError as exc:
        return _error(str(exc), 404)
    except PedidoNoPagadoDeOtroUsuarioError as exc:
        return _error(str(exc), 403)
    except PedidoNoModificableError as exc:
        return _error(str(exc), 409)
    except ErrorPasarela as exc:
        return _error(str(exc), 502)
    return jsonify(url=resultado.url, token=resultado.token)


@pedido_bp.delete("/pedidos/<uuid:pedido_id>")
@requiere_sesion()
def eliminar_pedido(pedido_id: UUID):
    try:
        _servicio_pedido_no_pagado().eliminar(pedido_id, _usuario_uuid())
    except PedidoNoPagadoNoEncontradoError as exc:
        return _error(str(exc), 404)
    except PedidoNoPagadoDeOtroUsuarioError as exc:
        return _error(str(exc), 403)
    except PedidoNoModificableError as exc:
        return _error(str(exc), 409)
    return jsonify(ok=True)


@pedido_bp.post("/pedidos/<uuid:pedido_id>/cancelar")
@requiere_sesion()
def cancelar_pedido(pedido_id: UUID):
    """El cliente cancela su propio pedido, hasta que entre en produccion."""
    try:
        pedido = _servicio_cambiar_estado().cancelar(pedido_id, _usuario_uuid())
    except PedidoNoEncontradoError as exc:
        return _error(str(exc), 404)
    except PedidoDeOtroUsuarioError as exc:
        return _error(str(exc), 403)
    except TransicionInvalidaError as exc:
        return _error(str(exc), 409)
    return jsonify(_a_publico_pedido(pedido))


@pedido_bp.post("/pedidos/<uuid:pedido_id>/aviso-cancelacion")
@requiere_sesion()
@rol_requerido("admin")
def avisar_cancelacion_cliente(pedido_id: UUID):
    """El admin confirma que Tuu acepto la anulacion: enciende el badge."""
    try:
        pedido = _servicio_notificar_cancelacion().informar_cliente(pedido_id)
    except AvisoPedidoNoEncontradoError as exc:
        return _error(str(exc), 404)
    except PedidoSinCancelarError as exc:
        return _error(str(exc), 409)
    return jsonify(
        aviso_cancelacion_en=pedido.aviso_cancelacion_en.isoformat()
        if pedido.aviso_cancelacion_en
        else None,
        aviso_cancelacion_pendiente=True,
    )


@pedido_bp.post("/pedidos/<uuid:pedido_id>/aviso-cancelacion/visto")
@requiere_sesion()
def marcar_aviso_cancelacion_visto(pedido_id: UUID):
    """El cliente abre el aviso: el badge se apaga (idempotente)."""
    pedido = _servicio_consulta().por_id(pedido_id)
    if pedido is None:
        return _error("Pedido no encontrado", 404)
    if not _es_dueno(pedido):
        return _error("No autorizado", 403)
    try:
        _servicio_notificar_cancelacion().marcar_visto(pedido_id)
    except AvisoPedidoNoEncontradoError as exc:
        return _error(str(exc), 404)
    return jsonify(ok=True, aviso_cancelacion_pendiente=False)


@pedido_bp.patch("/pedidos/<uuid:pedido_id>/estado")
@requiere_sesion()
@rol_requerido("admin")
def cambiar_estado_pedido(pedido_id: UUID):
    datos = request.get_json(silent=True) or {}
    try:
        pedido = _servicio_cambiar_estado().ejecutar(pedido_id, datos.get("estado"))
    except EstadoInvalidoError as exc:
        return _error(str(exc), 400)
    except PedidoNoEncontradoError as exc:
        return _error(str(exc), 404)
    except TransicionInvalidaError as exc:
        return _error(str(exc), 409)
    return jsonify(_a_publico_pedido(pedido, admin=True))


@pedido_bp.get("/pedidos/admin")
@requiere_sesion()
@rol_requerido("admin")
def listar_pedidos_admin():
    pedidos = _servicio_seguimiento().listar_todos()
    return jsonify(pedidos=[_a_publico_pedido(p, admin=True) for p in pedidos])


@pedido_bp.post("/pedidos/<uuid:pedido_id>/seguimiento")
@requiere_sesion()
@rol_requerido("admin")
def registrar_seguimiento(pedido_id: UUID):
    datos = request.get_json(silent=True) or {}
    try:
        pedido = _servicio_seguimiento().registrar_codigo(
            pedido_id, datos.get("codigo"), datos.get("transportista")
        )
    except ValueError as exc:
        estado = 404 if "no encontrado" in str(exc) else 400
        return _error(str(exc), estado)
    return jsonify(_a_publico_pedido(pedido, admin=True))


def _a_publico_seguimiento(pedido, seguimiento) -> dict:
    return {
        "id": str(pedido.id),
        "codigo_seguimiento": pedido.codigo_seguimiento,
        "transportista": pedido.transportista,
        "estado_seguimiento": pedido.estado_seguimiento,
        "seguimiento_actualizado_en": (
            pedido.seguimiento_actualizado_en.isoformat()
            if pedido.seguimiento_actualizado_en
            else None
        ),
        "seguimiento": (
            {
                "estado": seguimiento.estado,
                "descripcion": seguimiento.descripcion,
                "consultado_en": (
                    seguimiento.consultado_en.isoformat()
                    if seguimiento.consultado_en
                    else None
                ),
                "historial": [
                    {
                        "fecha": evento.fecha.isoformat() if evento.fecha else None,
                        "descripcion": evento.descripcion,
                        "sucursal": evento.sucursal,
                        "ciudad": evento.ciudad,
                        "estado": evento.estado,
                    }
                    for evento in seguimiento.historial
                ],
            }
            if seguimiento
            else None
        ),
    }


@pedido_bp.get("/pedidos/<uuid:pedido_id>/seguimiento")
@requiere_sesion()
def consultar_seguimiento(pedido_id: UUID):
    pedido = _servicio_consulta().por_id(pedido_id)
    if pedido is None:
        return _error("Pedido no encontrado", 404)
    if not _es_dueno(pedido):
        return _error("No autorizado", 403)
    try:
        pedido_actual, seguimiento = _servicio_seguimiento().sincronizar(pedido_id)
    except ValueError as exc:
        return _error(str(exc), 400)
    return jsonify(_a_publico_seguimiento(pedido_actual, seguimiento))


@pedido_bp.get("/pedidos/<uuid:pedido_id>/documento")
@requiere_sesion()
def consultar_documento(pedido_id: UUID):
    """Datos del comprobante electrónico del pedido (folio, montos, estado)."""
    pedido = _servicio_consulta().por_id(pedido_id)
    if pedido is None:
        return _error("Pedido no encontrado", 404)
    if not _es_dueno(pedido):
        return _error("No autorizado", 403)
    documento = _servicio_documento().por_pedido(pedido_id)
    if documento is None:
        return _error("El pedido no tiene documento electrónico", 404)
    return jsonify(_a_publico_documento(documento))


@pedido_bp.get("/pedidos/<uuid:pedido_id>/documento/pdf")
@requiere_sesion()
def descargar_documento_pdf(pedido_id: UUID):
    """PDF del comprobante, tal como lo devolvió el proveedor."""
    pedido = _servicio_consulta().por_id(pedido_id)
    if pedido is None:
        return _error("Pedido no encontrado", 404)
    if not _es_dueno(pedido):
        return _error("No autorizado", 403)
    documento = _servicio_documento().por_pedido(pedido_id)
    if documento is None:
        return _error("El pedido no tiene documento electrónico", 404)
    if not documento.pdf:
        return _error("El documento todavía no tiene PDF", 404)
    nombre = f"documento-{documento.folio or documento.id}.pdf"
    return send_file(
        BytesIO(documento.pdf),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=nombre,
    )


def _a_publico_documento(documento) -> dict:
    return {
        "id": str(documento.id),
        "tipo": documento.tipo.value,
        "estado": documento.estado.value,
        "folio": documento.folio,
        "rut_emisor": documento.rut_emisor,
        "rut_receptor": documento.rut_receptor,
        "razon_social_receptor": documento.razon_social_receptor,
        "giro_receptor": documento.giro_receptor,
        "direccion_receptor": documento.direccion_receptor,
        "comuna_receptor": documento.comuna_receptor,
        "monto_neto": documento.monto_neto,
        "iva": documento.iva,
        "monto_total": documento.monto_total,
        "fecha_emision": (
            documento.fecha_emision.isoformat() if documento.fecha_emision else None
        ),
        "error": documento.error,
        "tiene_pdf": bool(documento.pdf),
    }


@pedido_bp.post("/pago/crear")
@requiere_sesion()
def crear_pago():
    datos = request.get_json(silent=True) or {}
    if not datos.get("items"):
        return _error("items es obligatorio", 400)
    try:
        dto = IniciarPagoDTO(
            usuario_id=_usuario_uuid(),
            items=_items(datos),
            entrega=datos.get("entrega") or "retiro",
            cliente=datos.get("cliente") or None,
            total_esperado=_entero_opcional(datos.get("total")),
            clave_idempotencia=_clave_idempotencia(
                datos.get("claveIdempotencia") or datos.get("clave_idempotencia")
            ),
            guardar_datos=bool(datos.get("guardarDatos") or datos.get("guardar_datos")),
            cupon_codigo=str(datos.get("cuponCodigo") or datos.get("cupon_codigo") or "").strip().upper() or None,
        )
    except (ValueError, TypeError) as exc:
        return _error(f"Datos inválidos: {exc}", 400)

    try:
        resultado = _servicio_pago().iniciar(dto)
    except ValueError as exc:
        return _error(str(exc), 409)
    except ErrorPasarela as exc:
        return _error(str(exc), 502)
    return jsonify(url=resultado.url, token=resultado.token)


def _parametros_notificacion() -> dict:
    json_body = request.get_json(silent=True)
    if json_body:
        return json_body
    form = request.form.to_dict()
    if form:
        return form
    return request.args.to_dict()


def _cuerpo_confirmacion(resultado) -> dict:
    return {
        "estado": resultado.estado,
        "pedido_id": resultado.pedido_id,
        "mensaje": resultado.mensaje,
        "correo_enviado": resultado.correo_enviado,
    }


@pedido_bp.post("/pago/confirmar")
def confirmar_pago():
    try:
        resultado = _servicio_pago().confirmar(_parametros_notificacion())
    except ErrorPasarela as exc:
        return _error(str(exc), 400)
    return jsonify(**_cuerpo_confirmacion(resultado))


@pedido_bp.post("/pago/callback")
def callback_pago():
    try:
        resultado = _servicio_pago().confirmar(_parametros_notificacion())
    except ErrorPasarela as exc:
        return _error(str(exc), 400)
    return jsonify(**_cuerpo_confirmacion(resultado))