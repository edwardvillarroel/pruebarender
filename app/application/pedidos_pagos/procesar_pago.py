
from __future__ import annotations

import json
import logging
from typing import Any

from app.application.common.calculos import calcular_total_con_envio
from app.application.common.dto import IniciarPagoDTO, ResultadoConfirmacionPago
from app.application.common.facturacion import tipo_documento_de
from app.application.common.referencias import (
    codificar_referencia,
    decodificar_referencia,
)
from app.domain.entities.detalle_pedido import DetallePedido
from app.domain.entities.pago import Pago
from app.domain.entities.pedido import Pedido
from app.domain.entities.solicitud_diseno import EstadoSolicitud
from app.domain.enums import EstadoPago, EstadoPedido
from app.domain.interfaces.carrito_repository import CarritoRepository
from app.domain.interfaces.correo import ServicioCorreo
from app.domain.interfaces.facturacion import ServicioDocumentacionTributaria
from app.domain.interfaces.pasarela_pago import (
    ErrorPasarela,
    PasarelaPago,
    ResultadoIntentoPago,
    SolicitudPago,
)
from app.domain.interfaces.repositories import (
    ClaveIdempotenciaOcupada,
    PagoRepository,
    PedidoRepository,
    ProductoRepository,
)
from app.infrastructure.repositories.cupon_repository import CuponRepository
from app.infrastructure.repositories.usuario_repository import UsuarioRepository

logger = logging.getLogger(__name__)


class TotalEsperadoDistintoError(ValueError):
    """El total del servidor no es el que el cliente vio y acepto pagar."""


class ClaveIdempotenciaReutilizadaError(ValueError):
    """La clave de idempotencia ya corresponde a una operacion concluida."""


class ProcesarPago:
    def __init__(
        self,
        pedidos: PedidoRepository,
        pagos: PagoRepository,
        productos: ProductoRepository,
        pasarela: PasarelaPago,
        carritos: CarritoRepository,
        correo: ServicioCorreo | None = None,
        usuarios: UsuarioRepository | None = None,
        cupones: CuponRepository | None = None,
        documentacion: ServicioDocumentacionTributaria | None = None,
        cotizaciones: Any = None,
    ) -> None:
        self._pedidos = pedidos
        self._pagos = pagos
        self._productos = productos
        self._pasarela = pasarela
        self._carritos = carritos
        self._correo = correo
        self._usuarios = usuarios
        self._cupones = cupones
        self._documentacion = documentacion
        self._cotizaciones = cotizaciones

    def iniciar(self, dto: IniciarPagoDTO) -> ResultadoIntentoPago:
        reintento = self._buscar_reintento(dto)
        if reintento is not None:
            return reintento

        if getattr(dto, "cotizacion_id", None) is not None:
            return self._iniciar_cotizacion(dto)

        pedido, detalles = self._construir_pedido(dto)
        if getattr(dto, "cupon_codigo", None) and self._cupones:
            cupon = self._cupones.get_by_codigo(dto.cupon_codigo)
            if cupon and cupon.activo and not cupon.usado:
                total = int(pedido.total)
                if cupon.tipo == "porcentaje":
                    descuento = int(round(total * float(cupon.valor) / 100.0))
                else:
                    descuento = int(round(float(cupon.valor)))
                if descuento > 0:
                    if descuento > total:
                        descuento = total
                    total_desc = total - descuento
                    pedido.total = total_desc
                    pedido.descuento_cupon = descuento
                    pedido.cupon_codigo = dto.cupon_codigo
            else:
                raise ValueError("Cupón inválido o ya utilizado")

        self._validar_total_esperado(pedido.total, dto.total_esperado)
        self._pedidos.crear_con_detalles(pedido, detalles)

        if getattr(dto, "cupon_codigo", None) and self._cupones:
            cupon = self._cupones.get_by_codigo(dto.cupon_codigo)
            if cupon and cupon.activo and not cupon.usado:
                try:
                    self._cupones.marcar_usado(cupon, dto.usuario_id)
                except Exception:
                    logger.exception("No se pudo marcar cupón como usado")

        pago = Pago(
            pedido_id=pedido.id,
            monto=pedido.total,
            proveedor="tuu",
            clave_idempotencia=dto.clave_idempotencia,
        )
        try:
            self._pagos.add(pago)
        except ClaveIdempotenciaOcupada:
            self._descartar_pedido(pedido)
            reintento = self._buscar_reintento(dto)
            if reintento is not None:
                return reintento

            raise ClaveIdempotenciaReutilizadaError(
                "Hay otra operacion de pago en curso con esa clave. "
                "Espera a que termine e intenta de nuevo."
            ) from None

        solicitud_referencia = codificar_referencia(pedido.id)
        solicitud = SolicitudPago(
            monto=pedido.total,
            referencia=solicitud_referencia,
            descripcion=f"Pedido {solicitud_referencia} en ApoloVibes",
            nombre_cliente=self._nombre_cliente(dto.cliente),
            email_cliente=(dto.cliente or {}).get("email", ""),
            telefono_cliente=(dto.cliente or {}).get("telefono", ""),
            apellido_cliente=self._apellido_cliente(dto.cliente),
        )
        try:
            resultado = self._pasarela.crear_intento(solicitud)
        except ErrorPasarela:
            self._marcar_fallido(pedido, pago)
            raise

        pago.token = resultado.token
        pago.url_intento = resultado.url
        self._pagos.update(pago)
        return resultado

    def _buscar_reintento(self, dto: IniciarPagoDTO) -> ResultadoIntentoPago | None:
        """Resultado de un inicio de pago ya en curso con la misma clave.

        Sin clave, o si la clave no tiene pago vivo, devuelve `None` y el flujo
        sigue normal. La clave solo se reusa si el pedido es del mismo usuario
        que pregunta: si el pago existente es de otra sesion, se trata como
        inexistente en vez de filtrar la URL de un tercero.
        """
        if not dto.clave_idempotencia:
            return None

        pago = self._pagos.get_by_clave_idempotencia(dto.clave_idempotencia)
        if pago is None:
            return None

        pedido = self._pedidos.get_by_id(pago.pedido_id)
        if pedido is None or pedido.usuario_id != dto.usuario_id:
            return None

        if pago.estado != EstadoPago.PENDIENTE:
            raise ClaveIdempotenciaReutilizadaError(
                "Este pago ya fue procesado. Actualizá la pagina para "
                "continuar con una nueva operacion."
            )

        if not pago.url_intento:
            raise ClaveIdempotenciaReutilizadaError(
                "El pago anterior todavia se esta procesando. Espera unos "
                "segundos e intenta de nuevo."
            )

        return ResultadoIntentoPago(url=pago.url_intento, token=pago.token)

    def _descartar_pedido(self, pedido: Pedido) -> None:
        """Borra el pedido que perdio la carrera de idempotencia.

        No tiene pago asociado (el INSERT del pago fue el que falló), asi que
        no lo referencia nadie. Si el borrado falla tampoco se propaga el error:
        la prioridad es devolver el resultado del ganador, y un pedido huerfano
        pendiente es el mismo estado que deja un carrito abandonado.
        """
        try:
            self._pedidos.delete(pedido)
        except Exception:  # noqa: BLE001 - borrar el huerfano es best-effort
            logger.warning(
                "No se pudo borrar el pedido huerfano de la carrera de "
                "idempotencia: pedido_id=%s",
                pedido.id,
            )

    @staticmethod
    def _validar_total_esperado(total: int, esperado: int | None) -> None:
        """El cliente paga sobre el total que vio en pantalla.

        Si el precio cambio entre que armo el carrito y que confirmo, el total
        del servidor ya no es el que el cliente acepta pagar. Se aborta antes de
        crear el pedido para que no quede una orden por un precio que nadie
        confirmo. Sin `total_esperado` no se valida nada.
        """
        if esperado is None or esperado == total:
            return
        raise TotalEsperadoDistintoError(
            f"El total cambio: esperabas ${esperado:,}".replace(",", ".")
            + f" y ahora es ${total:,}".replace(",", ".")
            + ". Actualiza el carrito para continuar."
        )

    def confirmar(self, parametros: dict[str, str]) -> ResultadoConfirmacionPago:
        if not self._pasarela.verificar_firma(parametros):
            raise ErrorPasarela("Firma inválida de la pasarela de pagos")

        referencia = parametros.get("x_reference")
        if not referencia:
            raise ErrorPasarela("La notificación no incluye la referencia del pedido")
        try:
            pedido_id = decodificar_referencia(referencia)
        except ValueError:
            raise ErrorPasarela("Referencia de pedido inválida")

        pedido = self._pedidos.get_by_id(pedido_id)
        if pedido is None:
            raise ErrorPasarela("Pedido no encontrado")
        pago = self._pagos.get_by_pedido(pedido_id)

        resultado = (parametros.get("x_result") or "").lower()
        if resultado == "completed":
            if pago is not None and pago.estado == EstadoPago.COMPLETADO:
                self._emitir_documento(pedido)
                return ResultadoConfirmacionPago(
                    estado="completado", pedido_id=str(pedido.id),
                    mensaje="Pago ya confirmado",
                    cotizacion_id=self._cotizacion_id(pedido),
                )
            try:
                self._descontar_stock(pedido)
            except ValueError as exc:
                return self._rechazar(pedido, pago, str(exc))
            if pago is not None:
                pago.estado = EstadoPago.COMPLETADO
                self._pagos.update(pago)
            if pedido.cotizacion_id is None:
                self._carritos.eliminar(str(pedido.usuario_id))
            self._emitir_documento(pedido)
            correo_enviado = self._enviar_comprobante(
                pedido, pago.estado.value if pago is not None else "completado"
            )
            return ResultadoConfirmacionPago(
                estado="completado", pedido_id=str(pedido.id),
                mensaje="Pago confirmado",
                correo_enviado=correo_enviado,
                cotizacion_id=self._cotizacion_id(pedido),
            )

        if resultado in ("failed", "aborted", "cancelled"):
            if pago is not None and pago.estado == EstadoPago.FALLIDO:
                return ResultadoConfirmacionPago(
                    estado="fallido", pedido_id=str(pedido.id),
                    mensaje="Pago ya rechazado",
                    cotizacion_id=self._cotizacion_id(pedido),
                )
            return self._rechazar(pedido, pago, "Pago rechazado por la pasarela")

        return ResultadoConfirmacionPago(
            estado="pendiente", pedido_id=str(pedido.id),
            mensaje="El pago aún no ha sido procesado",
            cotizacion_id=self._cotizacion_id(pedido),
        )

    def _iniciar_cotizacion(self, dto: IniciarPagoDTO) -> ResultadoIntentoPago:
        """Abre el pago de una cotización aprobada usando un pedido real.

        La cotización no tiene un producto de catálogo, así que el pedido lleva
        una línea con el precio que asignó el administrador. El vínculo único
        `pedidos.cotizacion_id` evita que dos intentos generen dos pedidos.
        """
        if self._cotizaciones is None:
            raise ValueError("El pago de cotizaciones no está configurado")

        solicitud = self._cotizaciones.obtener_por_id(dto.cotizacion_id)
        if solicitud is None or solicitud.usuario_id != dto.usuario_id:
            raise ValueError("La cotización no existe o no pertenece al usuario")
        if solicitud.estado != EstadoSolicitud.APROBADA:
            raise ValueError("La cotización todavía no fue aprobada")
        precio = int(solicitud.precio or 0)
        if precio <= 0:
            raise ValueError("La cotización no tiene un precio asignado")

        existente = self._pedidos.get_by_cotizacion(solicitud.id)
        creado_nuevo = existente is None
        pago = None
        if existente is not None:
            pago = self._pagos.get_by_pedido(existente.id)
            if pago is not None and pago.estado == EstadoPago.COMPLETADO:
                raise ValueError("La cotización ya fue pagada")
            self._validar_total_esperado(int(existente.total), dto.total_esperado)
            pedido = existente
            if pedido.estado == EstadoPedido.CANCELADO:
                pedido.estado = EstadoPedido.PENDIENTE
                self._pedidos.update(pedido)
            solicitud_referencia = codificar_referencia(pedido.id)
        else:
            pedido, detalles = self._construir_pedido_cotizacion(
                dto, solicitud, precio
            )
            self._validar_total_esperado(int(pedido.total), dto.total_esperado)
            self._pedidos.crear_con_detalles(pedido, detalles)
            solicitud_referencia = codificar_referencia(pedido.id)

        if pago is not None:
            pago.estado = EstadoPago.PENDIENTE
            pago.monto = pedido.total
            pago.token = None
            pago.url_intento = None
            pago.clave_idempotencia = dto.clave_idempotencia
            self._pagos.update(pago)
        else:
            pago = Pago(
                pedido_id=pedido.id,
                monto=pedido.total,
                proveedor="tuu",
                clave_idempotencia=dto.clave_idempotencia,
            )
            try:
                self._pagos.add(pago)
            except ClaveIdempotenciaOcupada:
                if creado_nuevo:
                    self._descartar_pedido(pedido)
                reintento = self._buscar_reintento(dto)
                if reintento is not None:
                    return reintento
                raise ClaveIdempotenciaReutilizadaError(
                    "Hay otra operacion de pago en curso con esa clave. "
                    "Espera a que termine e intenta de nuevo."
                ) from None

        solicitud_pago = SolicitudPago(
            monto=pedido.total,
            referencia=solicitud_referencia,
            descripcion=f"Pedido {solicitud_referencia} en ApoloVibes",
            nombre_cliente=self._nombre_cliente(dto.cliente),
            email_cliente=(dto.cliente or {}).get("email", ""),
            telefono_cliente=(dto.cliente or {}).get("telefono", ""),
            apellido_cliente=self._apellido_cliente(dto.cliente),
        )
        try:
            resultado = self._pasarela.crear_intento(solicitud_pago)
        except ErrorPasarela:
            self._marcar_fallido(pedido, pago)
            raise

        pago.token = resultado.token
        pago.url_intento = resultado.url
        self._pagos.update(pago)
        return resultado

    def _construir_pedido_cotizacion(
        self, dto: IniciarPagoDTO, solicitud: Any, precio: int
    ) -> tuple[Pedido, list[DetallePedido]]:
        pedido = Pedido(
            usuario_id=dto.usuario_id,
            cotizacion_id=solicitud.id,
            direccion_envio=(
                json.dumps(dto.cliente, ensure_ascii=False) if dto.cliente else None
            ),
            entrega=dto.entrega,
            tipo_documento=tipo_documento_de((dto.cliente or {}).get("tipoDocumento")),
        )
        corto = str(solicitud.id).split("-")[0].upper()
        material = solicitud.material or "Impresión 3D"
        descripcion = f"Cotización #{corto} - {material}"
        cantidad = int(solicitud.cantidad or 1)
        if cantidad > 1:
            descripcion += f" x{cantidad}"
        detalle = DetallePedido(
            pedido_id=pedido.id,
            producto_id=None,
            cantidad=1,
            precio_unitario=precio,
            color=solicitud.color,
            nombre=descripcion[:150],
        )
        pedido.subtotal = precio
        pedido.descuento_productos = 0
        pedido.total = calcular_total_con_envio(precio, dto.entrega)
        pedido.detalles = [detalle]
        return pedido, [detalle]

    def _construir_pedido(self, dto: IniciarPagoDTO) -> tuple[Pedido, list[DetallePedido]]:
        if not dto.items:
            raise ValueError("No hay productos para generar el pedido")

        pedido = Pedido(
            usuario_id=dto.usuario_id,
            direccion_envio=(
                json.dumps(dto.cliente, ensure_ascii=False) if dto.cliente else None
            ),
            entrega=dto.entrega,
            tipo_documento=tipo_documento_de((dto.cliente or {}).get("tipoDocumento")),
        )
        detalles: list[DetallePedido] = []
        subtotal_lista = 0
        subtotal_final = 0
        for item in dto.items:
            producto = self._productos.get_by_id(item.producto_id)
            if producto is None or not producto.activo:
                raise ValueError("Uno de los productos del pedido ya no está disponible")
            if producto.stock < item.cantidad:
                raise ValueError(
                    f"No hay stock suficiente de «{producto.nombre}» "
                    f"(disponible: {producto.stock})"
                )
            precio_original = getattr(producto, "precio_original", None)
            if not (
                isinstance(precio_original, int)
                and precio_original > producto.precio
            ):
                precio_original = None
            detalles.append(
                DetallePedido(
                    pedido_id=pedido.id,
                    producto_id=item.producto_id,
                    cantidad=item.cantidad,
                    precio_unitario=producto.precio,
                    precio_original=precio_original,
                    color=getattr(item, "color", None),
                    nombre=producto.nombre,
                )
            )
            subtotal_lista += (precio_original or producto.precio) * item.cantidad
            subtotal_final += producto.precio * item.cantidad

        pedido.subtotal = subtotal_lista
        pedido.descuento_productos = max(0, subtotal_lista - subtotal_final)
        pedido.total = calcular_total_con_envio(subtotal_final, dto.entrega)
        pedido.detalles = detalles
        return pedido, detalles

    def _descontar_stock(self, pedido: Pedido) -> None:
        items = [
            (d.producto_id, d.cantidad)
            for d in pedido.detalles
            if d.producto_id is not None
        ]
        if not items:
            return
        if not self._productos.descontar_stock(items):
            producto = pedido.detalles[0].producto_id if pedido.detalles else "-"
            raise ValueError(
                f"No hay stock suficiente para completar el pedido "
                f"(producto {producto})"
            )

    def _marcar_fallido(self, pedido: Pedido, pago: Pago) -> None:
        pago.estado = EstadoPago.FALLIDO
        self._pagos.update(pago)
        self._pedidos.actualizar_estado(pedido.id, EstadoPedido.CANCELADO)

    def _emitir_documento(self, pedido: Pedido) -> None:
        """Emite el documento electrónico del pedido, si corresponde.

        Es best-effort a propósito: el pago ya está confirmado y el cliente
        tiene que recibir la confirmación igual, aunque el proveedor de
        documentos esté caído. El error queda registrado en la fila del
        documento y la emisión se reintenta en la próxima confirmación.
        """
        if self._documentacion is None:
            return
        try:
            self._documentacion.emitir_para_pedido(pedido.id)
        except Exception:  # noqa: BLE001 - el documento no puede romper el pago
            logger.exception(
                "No se pudo emitir el documento del pedido %s", pedido.id
            )

    def _enviar_comprobante(self, pedido: Pedido, estado_pago: str) -> bool:
        """Manda el comprobante y devuelve si se mando de verdad.

        El retorno existe para que la respuesta al cliente no prometa algo que
        no sabemos: el envio es best-effort y traga la excepcion, asi que sin
        este `bool` la pantalla de exito diria "te enviamos el comprobante"
        aunque el correo se haya perdido.
        """
        if self._correo is None:
            return False
        email = _email_del_cliente(pedido.direccion_envio)
        if not email:
            logger.info(
                "Pedido %s sin email de cliente: no se envio comprobante", pedido.id
            )
            return False
        try:
            self._correo.enviar_comprobante_pedido(pedido, email, estado_pago)
        except Exception:  # noqa: BLE001 - el correo no puede romper el pago
            logger.exception(
                "No se pudo enviar el comprobante del pedido %s a %s", pedido.id, email
            )
            return False
        return True

    def _rechazar(
        self, pedido: Pedido, pago: Pago | None, mensaje: str
    ) -> ResultadoConfirmacionPago:
        if pago is not None:
            pago.estado = EstadoPago.FALLIDO
            self._pagos.update(pago)
        self._pedidos.actualizar_estado(pedido.id, EstadoPedido.CANCELADO)
        return ResultadoConfirmacionPago(
            estado="fallido", pedido_id=str(pedido.id), mensaje=mensaje,
            cotizacion_id=self._cotizacion_id(pedido),
        )

    @staticmethod
    def _cotizacion_id(pedido: Pedido) -> str | None:
        return str(pedido.cotizacion_id) if pedido.cotizacion_id else None

    @staticmethod
    def _nombre_cliente(cliente: dict[str, Any] | None) -> str:
        if not cliente:
            return "Cliente"
        nombre = str(cliente.get("nombre", "") or "").strip()
        return nombre or "Cliente"

    @staticmethod
    def _apellido_cliente(cliente: dict[str, Any] | None) -> str:
        if not cliente:
            return "ApoloVibes"
        apellido = str(cliente.get("apellido", "") or "").strip()
        return apellido or "ApoloVibes"


def _email_del_cliente(direccion_envio: str | None) -> str | None:
    if not direccion_envio:
        return None
    try:
        datos = json.loads(direccion_envio)
    except (TypeError, ValueError):
        return None
    if not isinstance(datos, dict):
        return None
    email = str(datos.get("email") or "").strip()
    return email or None