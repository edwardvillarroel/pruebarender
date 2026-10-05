
from __future__ import annotations

import json
import logging
from typing import Any

from app.application.common.calculos import calcular_total_con_envio
from app.application.common.dto import IniciarPagoDTO, ResultadoConfirmacionPago
from app.application.common.referencias import (
    codificar_referencia,
    decodificar_referencia,
)
from app.domain.entities.detalle_pedido import DetallePedido
from app.domain.entities.pago import Pago
from app.domain.entities.pedido import Pedido
from app.domain.enums import EstadoPago, EstadoPedido
from app.domain.interfaces.carrito_repository import CarritoRepository
from app.domain.interfaces.correo import ServicioCorreo
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
    ) -> None:
        self._pedidos = pedidos
        self._pagos = pagos
        self._productos = productos
        self._pasarela = pasarela
        self._carritos = carritos
        self._correo = correo

    def iniciar(self, dto: IniciarPagoDTO) -> ResultadoIntentoPago:
        # Reintento primero: si la clave ya tiene un pago vivo, se devuelve su
        # resultado y no se crea nada. Va antes de construir el pedido para que
        # un doble click no deje ordenes huerfanas en la base.
        reintento = self._buscar_reintento(dto)
        if reintento is not None:
            return reintento

        pedido, detalles = self._construir_pedido(dto)
        # Antes de persistir: si el total no coincide, no queda ni pedido ni
        # pago creados, solo un 409 con el mensaje para el cliente.
        self._validar_total_esperado(pedido.total, dto.total_esperado)
        self._pedidos.crear_con_detalles(pedido, detalles)

        pago = Pago(
            pedido_id=pedido.id,
            monto=pedido.total,
            proveedor="tuu",
            clave_idempotencia=dto.clave_idempotencia,
        )
        try:
            self._pagos.add(pago)
        except ClaveIdempotenciaOcupada:
            # Carrera real: dos peticiones con la misma clave se cruzaron y las
            # dos llegaron al INSERT. El indice unico salta en la segunda.
            # El pedido recien creado queda huerfano (no tiene pago), asi que se
            # borra y se devuelve el resultado del ganador en vez de un 500.
            self._descartar_pedido(pedido)
            reintento = self._buscar_reintento(dto)
            if reintento is not None:
                return reintento
            # La clave la tiene un pago VIVO que no es de esta sesion: no hay
            # resultado propio que devolver. El indice es global, asi que la
            # clave no se puede reusar entre usuarios. Se responde con un 409
            # explicito en vez de dejar escapar `ClaveIdempotenciaOcupada` al
            # handler, que la convertiria en un 500.
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
        # El url no se puede reconstruir: sale de la respuesta de la pasarela.
        # Se persiste para que un reintento con la misma clave pueda devolver
        # exactamente el mismo destino en vez de abrir un segundo intento.
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
            # La operacion ya concluyo con esa clave. Devolver el url viejo
            # mandaria al cliente a un pago ya cobrado o ya cancelado, asi que
            # se informa y el frontend tiene que generar una clave nueva.
            raise ClaveIdempotenciaReutilizadaError(
                "Este pago ya fue procesado. Actualizá la pagina para "
                "continuar con una nueva operacion."
            )

        if not pago.url_intento:
            # El pago esta vivo pero sin url guardada: no hay nada seguro que
            # devolver. Caer por aqui significaria abrir un segundo intento
            # mientras el primero sigue vivo, que es justo lo que la clave
            # existe para evitar.
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
        # `f"{n:,}"` pone la coma de miles, que en espanol chileno se lee como
        # separador decimal ("$18,078" es ambiguo). El total es un entero de
        # pesos, asi que el punto de miles es lo unico que corresponde.
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
                return ResultadoConfirmacionPago(
                    estado="completado", pedido_id=str(pedido.id),
                    mensaje="Pago ya confirmado",
                )
            try:
                self._descontar_stock(pedido)
            except ValueError as exc:
                return self._rechazar(pedido, pago, str(exc))
            if pago is not None:
                pago.estado = EstadoPago.COMPLETADO
                self._pagos.update(pago)
            self._carritos.eliminar(str(pedido.usuario_id))
            # El comprobante lleva el estado del PAGO. Si no hay fila de pago
            # (pago locales que no la crearon), el estado es el de esta rama:
            # la pasarela dijo `completed`, o sea que el pago SI se concretó.
            correo_enviado = self._enviar_comprobante(
                pedido, pago.estado.value if pago is not None else "completado"
            )
            return ResultadoConfirmacionPago(
                estado="completado", pedido_id=str(pedido.id),
                mensaje="Pago confirmado",
                correo_enviado=correo_enviado,
            )

        if resultado in ("failed", "aborted", "cancelled"):
            if pago is not None and pago.estado == EstadoPago.FALLIDO:
                return ResultadoConfirmacionPago(
                    estado="fallido", pedido_id=str(pedido.id),
                    mensaje="Pago ya rechazado",
                )
            return self._rechazar(pedido, pago, "Pago rechazado por la pasarela")

        return ResultadoConfirmacionPago(
            estado="pendiente", pedido_id=str(pedido.id),
            mensaje="El pago aún no ha sido procesado",
        )

    def _construir_pedido(self, dto: IniciarPagoDTO) -> tuple[Pedido, list[DetallePedido]]:
        if not dto.items:
            raise ValueError("No hay productos para generar el pedido")

        pedido = Pedido(
            usuario_id=dto.usuario_id,
            direccion_envio=(
                json.dumps(dto.cliente, ensure_ascii=False) if dto.cliente else None
            ),
            entrega=dto.entrega,
        )
        detalles: list[DetallePedido] = []
        subtotal = 0
        for item in dto.items:
            producto = self._productos.get_by_id(item.producto_id)
            if producto is None or not producto.activo:
                raise ValueError("Uno de los productos del pedido ya no está disponible")
            if producto.stock < item.cantidad:
                raise ValueError(
                    f"No hay stock suficiente de «{producto.nombre}» "
                    f"(disponible: {producto.stock})"
                )
            detalles.append(
                DetallePedido(
                    pedido_id=pedido.id,
                    producto_id=item.producto_id,
                    cantidad=item.cantidad,
                    precio_unitario=producto.precio,
                    color=getattr(item, "color", None),
                    nombre=producto.nombre,
                )
            )
            subtotal += producto.precio * item.cantidad

        pedido.total = calcular_total_con_envio(subtotal, dto.entrega)
        pedido.detalles = detalles
        return pedido, detalles

    def _descontar_stock(self, pedido: Pedido) -> None:
        items = [(d.producto_id, d.cantidad) for d in pedido.detalles]
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
            estado="fallido", pedido_id=str(pedido.id), mensaje=mensaje
        )

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