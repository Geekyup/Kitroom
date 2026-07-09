import zipfile
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import (
    InvalidArchive,
    TooManyFilesInArchive,
    ZipSlipDetected,
)
from app.db.models.drum_kit_node import DrumKitNode, NodeType


class ArchiveService:
    def extract_and_validate(self, zip_path: str, kit_id: int) -> list[DrumKitNode]:
        """
        Валидирует приватный zip (settings.UPLOADS_STORAGE_ROOT) и распаковывает
        аудиофайлы в публичную зону settings.PUBLIC_STORAGE_ROOT/kits/{kit_id}/extracted/,
        сохраняя структуру папок — нужно для проигрывания через <audio src=...>.
        Оригинальный zip остаётся в приватной зоне для полного скачивания.
        """
        path = Path(zip_path)

        if not zipfile.is_zipfile(path):
            raise InvalidArchive("File is not a valid zip archive")

        extract_root = Path(settings.PUBLIC_STORAGE_ROOT) / "kits" / str(kit_id) / "extracted"
        extract_root.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(path) as zf:
            infos = [i for i in zf.infolist() if not i.filename.replace("\\", "/").endswith("/")]

            if len(infos) > settings.MAX_FILES_PER_KIT:
                raise TooManyFilesInArchive()

            for info in infos:
                self._assert_safe_path(info.filename)

            folder_paths = self._collect_folder_paths(zf.namelist())
            nodes = self._build_nodes(kit_id, infos, folder_paths, zf, extract_root)

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

    def _build_nodes(
        self,
        kit_id: int,
        infos: list[zipfile.ZipInfo],
        folder_paths: set[str],
        zf: zipfile.ZipFile,
        extract_root: Path,
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

            dest_path = extract_root / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            with zf.open(info) as source, open(dest_path, "wb") as target:
                target.write(source.read())

            duration_ms = self._read_duration_ms(dest_path)

            node = DrumKitNode(
                kit_id=kit_id,
                name=parts[-1],
                node_type=NodeType.FILE,
                relative_path=rel_path,
                file_format=extension.lstrip("."),
                duration_ms=duration_ms,
                storage_path=str(dest_path),
                order_index=order,
            )
            if parent_path is not None:
                node.parent = nodes_by_path[parent_path]

            nodes_by_path[rel_path] = node
            order += 1

        return list(nodes_by_path.values())

    def _read_duration_ms(self, file_path: Path) -> int | None:
        import soundfile as sf

        try:
            audio_info = sf.info(str(file_path))
            return int(audio_info.duration * 1000)
        except Exception:
            return None