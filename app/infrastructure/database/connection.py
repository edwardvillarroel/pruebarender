import uuid

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import LargeBinary
from sqlalchemy.types import TypeDecorator

db = SQLAlchemy()


class UuidRaw(TypeDecorator):
    """UUID almacenado como RAW(16) en Oracle.

    SQLAlchemy modela Uuid como texto (CHAR) en Oracle, pero el esquema usa
    RAW(16). Este tipo serializa/deserializa bytes <-> uuid.UUID.
    """

    impl = LargeBinary(16)
    cache_ok = True

    def process_literal_param(self, value, dialect):
        return self.process_bind_param(value, dialect)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value.bytes
        if isinstance(value, str):
            return uuid.UUID(value).bytes
        if isinstance(value, bytes):
            return value
        raise TypeError(f"Tipo no soportado para UUID: {type(value).__name__}")

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, bytes):
            return uuid.UUID(bytes=value)
        if isinstance(value, str):
            return uuid.UUID(value)
        return value