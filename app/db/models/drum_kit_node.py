from enum import StrEnum

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base


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