from datetime import date
from uuid import UUID

from app.domain.entities.venta_local import SesionVenta, VentaLocal, VentaLocalItem
from app.domain.enums import EstadoSesionVenta, MedioPago, Rol
from app.domain.interfaces.repositories import ProductoRepository
from app.domain.interfaces.venta_local_repository import VentaLocalRepository


class SesionNoAutorizada(ValueError):
    """El usuario intenta operar una sesión que no le pertenece."""


class GestionarVentaLocal:


    def __init__(self, repositorio: VentaLocalRepository, producto_repo: ProductoRepository) -> None:
        self._repositorio = repositorio
        self._producto_repo = producto_repo

    def abrir_sesion(self, lugar: str, usuario_id: UUID, fecha: date | None = None) -> SesionVenta:
        if not lugar or not lugar.strip():
            raise ValueError("El lugar es obligatorio")
        if self._repositorio.obtener_sesion_abierta_de(usuario_id) is not None:
            raise ValueError("Ya tienes una sesión de venta abierta. Ciérrala antes de abrir otra.")
        fecha = fecha or date.today()
        if self._repositorio.obtener_sesion_de_fecha(usuario_id, fecha) is not None:
            raise ValueError(
                "Ya registraste una sesión de venta para esta fecha. "
                "Solo se permite una sesión por día."
            )
        sesion = SesionVenta(
            lugar=lugar.strip(),
            fecha=fecha,
            usuario_id=usuario_id,
        )
        return self._repositorio.crear_sesion(sesion)

    def obtener_sesion_abierta(self, usuario_id: UUID) -> SesionVenta | None:
        return self._repositorio.obtener_sesion_abierta_de(usuario_id)

    def registrar_venta(
        self,
        sesion_id: UUID,
        medio_pago: str,
        items: list[tuple[UUID, int]],
        usuario_id: UUID,
    ) -> VentaLocal:
        sesion = self._repositorio.obtener_sesion_por_id(sesion_id)
        if sesion is None:
            raise ValueError("Sesión no encontrada")
        if sesion.estado != EstadoSesionVenta.ABIERTA.value:
            raise ValueError("La sesión ya está cerrada")
        if sesion.usuario_id != usuario_id:
            raise SesionNoAutorizada(
                "No puedes registrar ventas en una sesión que no es tuya"
            )
        if medio_pago not in (MedioPago.EFECTIVO.value, MedioPago.TUU.value):
            raise ValueError("Medio de pago inválido")
        if not items:
            raise ValueError("Debes agregar al menos un producto")

        lineas: list[VentaLocalItem] = []
        for producto_id, cantidad in items:
            producto = self._producto_repo.get_by_id(producto_id)
            if producto is None:
                raise ValueError(f"Producto no encontrado")
            if isinstance(cantidad, bool) or not isinstance(cantidad, int):
                raise ValueError("La cantidad debe ser un número entero mayor a cero")
            if cantidad <= 0:
                raise ValueError("La cantidad debe ser mayor a cero")
            if producto.stock < cantidad:
                raise ValueError(
                    f"No hay stock suficiente de «{producto.nombre}» (disponible: {producto.stock})"
                )
            lineas.append(
                VentaLocalItem(
                    producto_id=producto_id,
                    nombre=producto.nombre,
                    cantidad=cantidad,
                    precio_unitario=producto.precio,
                )
            )

        total = sum(item.cantidad * item.precio_unitario for item in lineas)
        venta = VentaLocal(
            sesion_id=sesion_id,
            medio_pago=medio_pago,
            items=lineas,
            total=total,
            usuario_id=usuario_id,
        )
        return self._repositorio.registrar_venta(venta)

    def cerrar_sesion(
        self, sesion_id: UUID, usuario_id: UUID, rol: str
    ) -> SesionVenta:
        sesion = self._repositorio.obtener_sesion_por_id(sesion_id)
        if sesion is None:
            raise ValueError("Sesión no encontrada")
        if sesion.estado != EstadoSesionVenta.ABIERTA.value:
            raise ValueError("La sesión ya está cerrada")
        if sesion.usuario_id != usuario_id and rol != Rol.ADMIN.value:
            raise SesionNoAutorizada(
                "Solo el dueño de la sesión o un administrador puede cerrarla"
            )
        cerrada = self._repositorio.cerrar_sesion(sesion_id)
        if cerrada is None:
            raise ValueError("Sesión no encontrada")
        return cerrada

    def listar_reportes(self, usuario_id: UUID | None = None) -> list[SesionVenta]:
        return self._repositorio.listar_reportes(usuario_id)

    def obtener_reporte(self, sesion_id: UUID) -> SesionVenta | None:
        return self._repositorio.obtener_reporte(sesion_id)

    def obtener_ventas_de_sesion(self, sesion_id: UUID) -> list[VentaLocal]:
        return self._repositorio.obtener_ventas_de_sesion(sesion_id)