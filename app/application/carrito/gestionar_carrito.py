from uuid import UUID

from app.domain.entities.carrito import Carrito, ItemCarrito
from app.domain.interfaces.carrito_repository import CarritoRepository


class ItemCarritoNoEncontrado(Exception):
    """El ítem indicado no existe en el carrito del usuario."""


class GestionarCarrito:


    def __init__(self, repositorio: CarritoRepository) -> None:
        self._repositorio = repositorio

    def obtener(self, usuario_id: str) -> Carrito:
        carrito = self._repositorio.obtener(usuario_id)
        if carrito is None:
            carrito = Carrito(usuario_id=usuario_id)
            self._repositorio.guardar(carrito)
        return carrito

    def agregar_item(
        self, usuario_id: str, producto_id: str, cantidad: int, color: str | None = None
    ) -> Carrito:

        self._validar_cantidad(cantidad)
        color = (color or "").strip() or None
        carrito = self.obtener(usuario_id)
        for item in carrito.items:
            if item.producto_id == producto_id and (item.color or None) == color:
                item.cantidad += cantidad
                break
        else:
            carrito.items.append(
                ItemCarrito(producto_id=producto_id, cantidad=cantidad, color=color)
            )
        return self._repositorio.guardar(carrito)

    def actualizar_cantidad(self, usuario_id: str, item_id: UUID, cantidad: int) -> Carrito:
        self._validar_cantidad(cantidad)
        carrito = self.obtener(usuario_id)
        for item in carrito.items:
            if item.id == item_id:
                item.cantidad = cantidad
                return self._repositorio.guardar(carrito)
        raise ItemCarritoNoEncontrado()

    def eliminar_item(self, usuario_id: str, item_id: UUID) -> Carrito:
        carrito = self.obtener(usuario_id)
        for item in carrito.items:
            if item.id == item_id:
                carrito.items.remove(item)
                return self._repositorio.guardar(carrito)
        raise ItemCarritoNoEncontrado()

    def vaciar(self, usuario_id: str) -> Carrito:
        carrito = self.obtener(usuario_id)
        carrito.items = []
        return self._repositorio.guardar(carrito)

    @staticmethod
    def _validar_cantidad(cantidad: int) -> None:
        if cantidad < 1:
            raise ValueError("La cantidad debe ser un entero mayor a cero")