from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models.drum_kit import KitStatus


class KitCreate(BaseModel):
    title: str
    genre: str
    tags: list[str] = []
    description: str | None = None


class KitUpdate(BaseModel):
    title: str | None = None
    genre: str | None = None
    tags: list[str] | None = None
    description: str | None = None


class KitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    status: KitStatus
    error_message: str | None
    size_bytes: int
    genre: str
    tags: list[str]
    description: str | None
    cover_path: str | None
    downloads_count: int
    sound_count: int
    created_at: datetime

    owner_id: int | None = None
    owner_username: str | None = None
    owner_avatar_path: str | None = None


class KitStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    status: KitStatus
    error_message: str | None


class KitCatalogItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    author: str  
    owner_username: str 
    owner_avatar_path: str | None = None  
    genre: str
    tags: list[str]
    cover_path: str | None
    sound_count: int
    downloads_count: int
    size_bytes: int
    status: KitStatus
    error_message: str | None


class KitUploadInitOut(BaseModel):
    kit_id: int
    slug: str
    upload_url: str
    object_key: str