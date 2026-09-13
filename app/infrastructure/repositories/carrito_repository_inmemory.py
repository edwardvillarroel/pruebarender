import threading
from threading import Lock

from app.domain.entities.carrito import Carrito
from app.domain.interfaces.carrito_repository import CarritoRepository


class CarritoRepositoryEnMemoria(CarritoRepository):
    """Repositorio del carrito en memoria (por usuario/sesión).

    Fase de desarrollo: el carrito vive solo en el proceso del servidor y se
    pierde al reiniciarlo. Reemplazable por una implementación con SQLAlchemy
    que cumpla el mismo contrato (`CarritoRepository`), sin tocar la capa de
    aplicación ni las rutas.
    """

    def __init__(self) -> None:
        self._carritos: dict[str, Carrito] = {}
        self._lock: Lock = threading.Lock()

    def obtener(self, usuario_id: str) -> Carrito | None:
        with self._lock:
            return self._carritos.get(usuario_id)

    def guardar(self, carrito: Carrito) -> Carrito:
        with self._lock:
            self._carritos[carrito.usuario_id] = carrito
        return carrito

    def eliminar(self, usuario_id: str) -> None:
        with self._lock:
            self._carritos.pop(usuario_id, None)