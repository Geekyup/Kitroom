from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base


class KitStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DrumKit(Base):
    __tablename__ = "drum_kits"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    status: Mapped[KitStatus] = mapped_column(default=KitStatus.PENDING)
    error_message: Mapped[str | None] = mapped_column(String(1000), default=None)

    original_zip_path: Mapped[str] = mapped_column(String(1000))
    size_bytes: Mapped[int] = mapped_column(BigInteger)

    genre: Mapped[str] = mapped_column(String(50))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    description: Mapped[str | None] = mapped_column(String(2000), default=None)
    cover_path: Mapped[str | None] = mapped_column(String(1000), default=None)
    downloads_count: Mapped[int] = mapped_column(default=0)
    sound_count: Mapped[int] = mapped_column(default=0)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    owner: Mapped["User"] = relationship(back_populates="kits")
    nodes: Mapped[list["DrumKitNode"]] = relationship(
        back_populates="kit",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )