from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.db.models.drum_kit_node import NodeType


class NodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    node_type: NodeType
    file_format: str | None
    duration_ms: int | None
    order_index: int
    sound_url: str | None = None
    children: list["NodeOut"] = []


class KitTreeOut(BaseModel):
    kit_slug: str
    kit_title: str
    root: list[NodeOut]