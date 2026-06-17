import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, DateTime, String, func
from sqlmodel import Field, SQLModel


class Role(StrEnum):
    user = "user"
    admin = "admin"


class UserBase(SQLModel):
    email: str = Field(unique=True, index=True, max_length=255)
    role: Role = Field(default=Role.user)
    is_active: bool = Field(default=True)


class User(UserBase, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    # Explicit String column so SQLAlchemy does not infer a native PostgreSQL ENUM,
    # which would require a separate CREATE TYPE and mismatch the VARCHAR migration.
    role: Role = Field(
        default=Role.user,
        sa_column=Column(String, nullable=False, server_default="user"),
    )

    # Server-managed timestamps: the DB sets them, Python reads them after flush.
    # onupdate on updated_at means the DB refreshes it on every UPDATE automatically.
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        ),
    )
