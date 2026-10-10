from typing import Any
from uuid import UUID

from app.infrastructure.database.connection import db


class RepositoryBase:
    model = None

    def get_by_id(self, entity_id: UUID) -> Any:
        return db.session.get(self.model, entity_id)

    def list(self, *filters: Any) -> list[Any]:
        query = db.session.query(self.model)
        if filters:
            query = query.filter(*filters)
        return query.all()

    def add(self, entity: Any) -> Any:
        db.session.add(entity)
        return entity

    def update(self, entity: Any) -> Any:
        db.session.merge(entity)
        return entity

    def delete(self, entity: Any) -> None:
        db.session.delete(entity)