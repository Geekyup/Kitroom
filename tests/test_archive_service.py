import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from app.core.exceptions import InvalidArchive, TooManyFilesInArchive, ZipSlipDetected
from app.db.models.drum_kit_node import NodeType
from app.services.archive_service import ArchiveService
from app.storage.local import LocalStorageBackend


def make_zip_bytes(files: dict[str, bytes]) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


@pytest.fixture
def local_storage(tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOADS_STORAGE_ROOT", str(tmp_path))
    return LocalStorageBackend()


@pytest.fixture
def archive_service(local_storage):
    return ArchiveService(storage=local_storage)


async def upload_zip(storage: LocalStorageBackend, files: dict[str, bytes], key: str = "kits/uploads/test.zip") -> str:
    data = make_zip_bytes(files)
    await storage.save_bytes(data, key)
    return key


class TestZipSlipProtection:
    async def test_rejects_path_traversal_with_dotdot(self, archive_service, local_storage):
        key = await upload_zip(local_storage, {"../../etc/passwd": b"evil"})
        with pytest.raises(ZipSlipDetected):
            await archive_service.extract_and_validate(key, kit_id=1)

    async def test_rejects_nested_path_traversal(self, archive_service, local_storage):
        key = await upload_zip(local_storage, {"kicks/../../secrets.wav": b"evil"})
        with pytest.raises(ZipSlipDetected):
            await archive_service.extract_and_validate(key, kit_id=1)

    async def test_rejects_absolute_path(self, archive_service, local_storage):
        key = await upload_zip(local_storage, {"/etc/passwd": b"evil"})
        with pytest.raises(ZipSlipDetected):
            await archive_service.extract_and_validate(key, kit_id=1)

    def test_assert_safe_path_rejects_absolute_path_directly(self, archive_service):
        with pytest.raises(ZipSlipDetected):
            archive_service._assert_safe_path("/etc/passwd")

    def test_assert_safe_path_rejects_windows_style_absolute_path(self, archive_service):
        with pytest.raises(ZipSlipDetected):
            archive_service._assert_safe_path("C:\\Windows\\System32\\config")

    def test_assert_safe_path_rejects_dotdot_directly(self, archive_service):
        with pytest.raises(ZipSlipDetected):
            archive_service._assert_safe_path("../../etc/passwd")

    def test_assert_safe_path_accepts_normal_relative_path(self, archive_service):
        archive_service._assert_safe_path("kicks/kick1.wav") 

    def test_assert_safe_path_rejects_unc_path(self, archive_service):
        with pytest.raises(ZipSlipDetected):
            archive_service._assert_safe_path("//server/share/file.wav")

    async def test_accepts_normal_relative_paths(self, archive_service, local_storage):
        key = await upload_zip(
            local_storage,
            {"kicks/kick1.wav": b"RIFF....WAVEfmt "},
        )
        try:
            await archive_service.extract_and_validate(key, kit_id=1)
        except ZipSlipDetected:
            pytest.fail("Легитимный относительный путь не должен считаться zip-slip")
        except Exception:
            pass  


class TestFileCountLimit:
    async def test_rejects_archive_with_too_many_files(self, archive_service, local_storage, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "MAX_FILES_PER_KIT", 3)
        files = {f"sounds/kick{i}.wav": b"data" for i in range(5)}
        key = await upload_zip(local_storage, files)

        with pytest.raises(TooManyFilesInArchive):
            await archive_service.extract_and_validate(key, kit_id=1)

    async def test_accepts_archive_within_limit(self, archive_service, local_storage, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "MAX_FILES_PER_KIT", 10)
        files = {f"sounds/kick{i}.wav": b"data" for i in range(3)}
        key = await upload_zip(local_storage, files)

        nodes = await archive_service.extract_and_validate(key, kit_id=1)
        assert len(nodes) > 0


class TestInvalidArchive:
    async def test_rejects_non_zip_file(self, archive_service, local_storage):
        key = "kits/uploads/not-a-zip.zip"
        await local_storage.save_bytes(b"this is definitely not a zip file", key)

        with pytest.raises(InvalidArchive):
            await archive_service.extract_and_validate(key, kit_id=1)

    async def test_rejects_empty_archive(self, archive_service, local_storage):
        key = await upload_zip(local_storage, {})
        with pytest.raises(InvalidArchive):
            await archive_service.extract_and_validate(key, kit_id=1)

    async def test_rejects_archive_with_only_non_audio_files(self, archive_service, local_storage):
        key = await upload_zip(local_storage, {"readme.txt": b"hello"})
        with pytest.raises(InvalidArchive):
            await archive_service.extract_and_validate(key, kit_id=1)


class TestTreeBuilding:
    async def test_flat_files_become_root_nodes(self, archive_service, local_storage):
        key = await upload_zip(
            local_storage,
            {
                "kick.wav": b"data1",
                "snare.wav": b"data2",
            },
        )
        nodes = await archive_service.extract_and_validate(key, kit_id=1)

        assert len(nodes) == 2
        assert all(n.node_type == NodeType.FILE for n in nodes)
        assert all(n.parent is None for n in nodes)

    async def test_nested_folders_only_created_when_containing_audio(self, archive_service, local_storage):
        key = await upload_zip(
            local_storage,
            {
                "kicks/kick1.wav": b"data1",
                "empty_folder/notes.txt": b"just text, no audio here",
            },
        )
        nodes = await archive_service.extract_and_validate(key, kit_id=1)

        folder_names = {n.name for n in nodes if n.node_type == NodeType.FOLDER}
        assert "kicks" in folder_names
        assert "empty_folder" not in folder_names

    async def test_file_node_has_parent_folder(self, archive_service, local_storage):
        key = await upload_zip(
            local_storage,
            {"kicks/kick1.wav": b"data1"},
        )
        nodes = await archive_service.extract_and_validate(key, kit_id=1)

        file_node = next(n for n in nodes if n.node_type == NodeType.FILE)
        folder_node = next(n for n in nodes if n.node_type == NodeType.FOLDER)

        assert file_node.parent is folder_node
        assert folder_node.name == "kicks"

    async def test_non_audio_extensions_are_skipped(self, archive_service, local_storage):
        key = await upload_zip(
            local_storage,
            {
                "kick.wav": b"data1",
                "cover.jpg": b"imagedata",
                "notes.txt": b"just some notes",
            },
        )
        nodes = await archive_service.extract_and_validate(key, kit_id=1)

        file_names = {n.name for n in nodes if n.node_type == NodeType.FILE}
        assert file_names == {"kick.wav"}

    async def test_all_supported_audio_extensions_are_included(self, archive_service, local_storage):
        key = await upload_zip(
            local_storage,
            {
                "a.wav": b"data",
                "b.mp3": b"data",
                "c.aiff": b"data",
                "d.flac": b"data",
            },
        )
        nodes = await archive_service.extract_and_validate(key, kit_id=1)
        file_names = {n.name for n in nodes if n.node_type == NodeType.FILE}
        assert file_names == {"a.wav", "b.mp3", "c.aiff", "d.flac"}


class TestContentTypeDetection:
    def test_known_extensions(self, archive_service):
        assert archive_service._content_type_for(".wav") == "audio/wav"
        assert archive_service._content_type_for(".mp3") == "audio/mpeg"
        assert archive_service._content_type_for(".aiff") == "audio/aiff"
        assert archive_service._content_type_for(".flac") == "audio/flac"

    def test_unknown_extension_falls_back_to_octet_stream(self, archive_service):
        assert archive_service._content_type_for(".xyz") == "application/octet-stream"


class TestDurationReading:
    def test_invalid_audio_data_returns_none_instead_of_raising(self, archive_service):
        result = archive_service._read_duration_ms(b"not actually audio data")
        assert result is None
