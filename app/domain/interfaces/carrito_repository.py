from abc import ABC, abstractmethod

from app.domain.entities.carrito import Carrito


class CarritoRepository(ABC):
    @abstractmethod
    def obtener(self, usuario_id: str) -> Carrito | None:
        raise NotImplementedError

    @abstractmethod
    def guardar(self, carrito: Carrito) -> Carrito:
        raise NotImplementedError

    @abstractmethod
    def eliminar(self, usuario_id: str) -> None:
        raise NotImplementedError