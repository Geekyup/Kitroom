import logging
import tempfile
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
from app.storage.factory import StorageBackend, get_storage_backend

logger = logging.getLogger("kitroom.archive")


class ArchiveService:

    def __init__(self, storage: StorageBackend | None = None):
        self.storage = storage or get_storage_backend()

    async def extract_and_validate(self, zip_key: str, kit_id: int) -> list[DrumKitNode]:
        with tempfile.TemporaryDirectory(prefix=f"kit-{kit_id}-") as tmp_dir:
            zip_path = Path(tmp_dir) / "archive.zip"

            logger.info("kit=%s скачивание архива %s из B2 на диск", kit_id, zip_key)
            size = await self.storage.download_to_file(zip_key, str(zip_path))
            logger.info("kit=%s архив скачан (%d bytes)", kit_id, size)

            if not zipfile.is_zipfile(zip_path):
                raise InvalidArchive("File is not a valid zip archive")

            extract_prefix = f"kits/{kit_id}/extracted"

            with zipfile.ZipFile(zip_path) as zf:
                infos = [i for i in zf.infolist() if not i.filename.replace("\\", "/").endswith("/")]

                if len(infos) > settings.MAX_FILES_PER_KIT:
                    raise TooManyFilesInArchive()

                for info in infos:
                    self._assert_safe_path(info.filename)

                folder_paths = self._collect_folder_paths(zf.namelist())
                logger.info("kit=%s найдено %d файлов, %d папок", kit_id, len(infos), len(folder_paths))
                nodes = await self._build_nodes(kit_id, infos, folder_paths, zf, extract_prefix)

        if not nodes:
            raise InvalidArchive("Archive is empty")

        logger.info("kit=%s обработка завершена, %d нод создано", kit_id, len(nodes))
        return nodes

    def _assert_safe_path(self, filename: str) -> None:
        cleaned = filename.replace("\\", "/")

        if cleaned.startswith("/"):
            raise ZipSlipDetected()

        # диск-буква: "C:/...", "d:/..."
        if len(cleaned) >= 2 and cleaned[1] == ":" and cleaned[0].isalpha():
            raise ZipSlipDetected()

        # UNC-путь: "//server/share/..."
        if cleaned.startswith("//"):
            raise ZipSlipDetected()

        parts = [p for p in cleaned.split("/") if p not in ("", ".")]
        #if ".." in parts:
        #   raise ZipSlipDetected()

    def _collect_folder_paths(self, namelist: list[str]) -> set[str]:
        folders: set[str] = set()
        for name in namelist:
            parts = Path(name.replace("\\", "/")).parts
            for i in range(1, len(parts)):
                folders.add("/".join(parts[:i]))
        return folders

    def _folders_with_audio(
        self, infos: list[zipfile.ZipInfo], folder_paths: set[str]
    ) -> set[str]:

        non_empty: set[str] = set()

        for info in infos:
            rel_path = info.filename.replace("\\", "/")
            extension = Path(rel_path).suffix.lower()
            if extension not in settings.ALLOWED_AUDIO_EXTENSIONS:
                continue

            parts = rel_path.split("/")
            for i in range(1, len(parts)):
                non_empty.add("/".join(parts[:i]))

        return non_empty & folder_paths

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


        non_empty_folders = self._folders_with_audio(infos, folder_paths)

        for folder in sorted(non_empty_folders, key=lambda p: p.count("/")):
            parts = folder.split("/")
            parent_path = "/".join(parts[:-1]) if len(parts) > 1 else None

            node = DrumKitNode(
                kit_id=kit_id,
                name=parts[-1],
                node_type=NodeType.FOLDER,
                relative_path=folder,
                order_index=order,
            )
            if parent_path is not None and parent_path in nodes_by_path:
                node.parent = nodes_by_path[parent_path]

            nodes_by_path[folder] = node
            order += 1

        upload_items: list[tuple[bytes, str, str]] = []
        file_meta: list[tuple[str, list[str], str | None, str, str, bytes]] = []

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

            upload_items.append((data, object_key, content_type))
            file_meta.append((rel_path, parts, parent_path, extension, object_key, data))

        logger.info("kit=%s загрузка %d аудиофайлов в B2 (batch)", kit_id, len(upload_items))
        await self.storage.save_many_bytes(upload_items)
        logger.info("kit=%s все аудиофайлы загружены", kit_id)

        for rel_path, parts, parent_path, extension, object_key, data in file_meta:
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