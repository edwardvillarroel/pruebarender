from abc import ABC, abstractmethod

from app.domain.entities.carrito import Carrito


class CarritoRepository(ABC):
    """Almacenamiento del carrito por usuario/sesión.

    La implementación actual es en memoria (fase de desarrollo). Cuando exista
    persistencia real se implementa este contrato con SQLAlchemy sin tocar la
    capa de aplicación.
    """

    @abstractmethod
    def obtener(self, usuario_id: str) -> Carrito | None:
        raise NotImplementedError

    @abstractmethod
    def guardar(self, carrito: Carrito) -> Carrito:
        raise NotImplementedError

    @abstractmethod
    def eliminar(self, usuario_id: str) -> None:
        raise NotImplementedError