from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, ForeignKey, JSON, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


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

    # User живёт в app.auth.models — межмодульная связь (см. пояснение там же).
    owner: Mapped["User"] = relationship(back_populates="kits")
    nodes: Mapped[list["DrumKitNode"]] = relationship(
        back_populates="kit",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class NodeType(StrEnum):
    FOLDER = "folder"
    FILE = "file"


class DrumKitNode(Base):
    __tablename__ = "drum_kit_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    kit_id: Mapped[int] = mapped_column(ForeignKey("drum_kits.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("drum_kit_nodes.id", ondelete="CASCADE"), default=None, index=True
    )

    name: Mapped[str] = mapped_column(String(255))
    node_type: Mapped[NodeType]
    relative_path: Mapped[str] = mapped_column(String(1000))

    file_format: Mapped[str | None] = mapped_column(String(20), default=None)
    duration_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    storage_path: Mapped[str | None] = mapped_column(String(1000), default=None)

    order_index: Mapped[int] = mapped_column(default=0)

    kit: Mapped["DrumKit"] = relationship(back_populates="nodes")
    parent: Mapped["DrumKitNode | None"] = relationship(
        remote_side="DrumKitNode.id",
        back_populates="children",
    )
    children: Mapped[list["DrumKitNode"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
