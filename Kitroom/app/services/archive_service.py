import zipfile
from io import BytesIO
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import (
    InvalidArchive,
    TooManyFilesInArchive,
    ZipSlipDetected,
)
from app.db.models.drum_kit_node import DrumKitNode, NodeType
from app.storage.b2 import B2StorageBackend


class ArchiveService:
    """
    Скачивает приватный zip из B2, валидирует и распаковывает аудиофайлы,
    заливая каждый обратно в B2 под kits/{kit_id}/extracted/... —
    сохраняя структуру папок, нужную для проигрывания через <audio src=...>.
    Оригинальный zip остаётся в B2 под kits/uploads/ для полного скачивания.
    """

    def __init__(self, storage: B2StorageBackend | None = None):
        self.storage = storage or B2StorageBackend()

    async def extract_and_validate(self, zip_key: str, kit_id: int) -> list[DrumKitNode]:
        zip_bytes = await self.storage.get_bytes(zip_key)
        buffer = BytesIO(zip_bytes)

        if not zipfile.is_zipfile(buffer):
            raise InvalidArchive("File is not a valid zip archive")

        extract_prefix = f"kits/{kit_id}/extracted"

        with zipfile.ZipFile(buffer) as zf:
            infos = [i for i in zf.infolist() if not i.filename.replace("\\", "/").endswith("/")]

            if len(infos) > settings.MAX_FILES_PER_KIT:
                raise TooManyFilesInArchive()

            for info in infos:
                self._assert_safe_path(info.filename)

            folder_paths = self._collect_folder_paths(zf.namelist())
            nodes = await self._build_nodes(kit_id, infos, folder_paths, zf, extract_prefix)

        if not nodes:
            raise InvalidArchive("Archive is empty")

        return nodes

    def _assert_safe_path(self, filename: str) -> None:
        normalized = Path(filename.replace("\\", "/"))
        if normalized.is_absolute():
            raise ZipSlipDetected()
        if ".." in normalized.parts:
            raise ZipSlipDetected()

    def _collect_folder_paths(self, namelist: list[str]) -> set[str]:
        folders: set[str] = set()
        for name in namelist:
            parts = Path(name.replace("\\", "/")).parts
            for i in range(1, len(parts)):
                folders.add("/".join(parts[:i]))
        return folders

    async def _build_nodes(
        self,
        kit_id: int,
        infos: list[zipfile.ZipInfo],
        folder_paths: set[str],
        zf: zipfile.ZipFile,
        extract_prefix: str,
    ) -> list[DrumKitNode]:
        nodes_by_path: dict[str, DrumKitNode] = {}
        order = 0

        for folder in sorted(folder_paths, key=lambda p: p.count("/")):
            parts = folder.split("/")
            parent_path = "/".join(parts[:-1]) if len(parts) > 1 else None

            node = DrumKitNode(
                kit_id=kit_id,
                name=parts[-1],
                node_type=NodeType.FOLDER,
                relative_path=folder,
                order_index=order,
            )
            if parent_path is not None:
                node.parent = nodes_by_path[parent_path]

            nodes_by_path[folder] = node
            order += 1

        for info in infos:
            rel_path = info.filename.replace("\\", "/")
            parts = rel_path.split("/")
            parent_path = "/".join(parts[:-1]) if len(parts) > 1 else None
            extension = Path(rel_path).suffix.lower()

            if extension not in settings.ALLOWED_AUDIO_EXTENSIONS:
                continue

            with zf.open(info) as source:
                data = source.read()

            object_key = f"{extract_prefix}/{rel_path}"
            content_type = self._content_type_for(extension)
            await self.storage.save_bytes(data, object_key, content_type=content_type)

            duration_ms = self._read_duration_ms(data)

            node = DrumKitNode(
                kit_id=kit_id,
                name=parts[-1],
                node_type=NodeType.FILE,
                relative_path=rel_path,
                file_format=extension.lstrip("."),
                duration_ms=duration_ms,
                storage_path=object_key,
                order_index=order,
            )
            if parent_path is not None:
                node.parent = nodes_by_path[parent_path]

            nodes_by_path[rel_path] = node
            order += 1

        return list(nodes_by_path.values())

    def _content_type_for(self, extension: str) -> str:
        return {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".aiff": "audio/aiff",
            ".flac": "audio/flac",
        }.get(extension, "application/octet-stream")

    def _read_duration_ms(self, data: bytes) -> int | None:
        import soundfile as sf

        try:
            audio_info = sf.info(BytesIO(data))
            return int(audio_info.duration * 1000)
        except Exception:
            return None
