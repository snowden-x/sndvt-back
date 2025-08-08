"""Custom SQL types for cross-dialect compatibility."""

import uuid
from typing import Optional

from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID


class GUID(TypeDecorator):
    """Platform-independent GUID/UUID type.

    - On PostgreSQL, stores as native UUID (as_uuid=True)
    - On other databases (e.g., SQLite), stores as CHAR(36) string
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PostgresUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Optional[object], dialect):
        if value is None:
            return value

        # Normalize to UUID object first
        if isinstance(value, uuid.UUID):
            normalized = value
        else:
            # Accept strings/ints that can be coerced
            normalized = uuid.UUID(str(value))

        if dialect.name == "postgresql":
            return normalized
        return str(normalized)

    def process_result_value(self, value: Optional[object], dialect):
        if value is None:
            return value

        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


