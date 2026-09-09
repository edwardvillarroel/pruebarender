from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from uuid import UUID

T = TypeVar("T")


class RepositoryBase(ABC, Generic[T]):
    @abstractmethod
    def get_by_id(self, entity_id: UUID) -> T | None:
        raise NotImplementedError

    @abstractmethod
    def list(self, *filters: Any) -> list[T]:
        raise NotImplementedError

    @abstractmethod
    def add(self, entity: T) -> T:
        raise NotImplementedError

    @abstractmethod
    def update(self, entity: T) -> T:
        raise NotImplementedError

    @abstractmethod
    def delete(self, entity: T) -> None:
        raise NotImplementedError