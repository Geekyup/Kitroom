from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from botocore.exceptions import ClientError

from app.core.exceptions import ArchiveTooLarge, KitNotReady, NotKitOwner, UploadNotFound
from app.db.models.drum_kit import KitStatus
from app.services.kit_service import KitService


def make_kit(id=1, owner_id=1, status=KitStatus.READY, original_zip_path="kits/uploads/abc.zip", slug="my-kit-abc123"):
    owner = SimpleNamespace(id=owner_id, username="owner", avatar_path=None)
    return SimpleNamespace(
        id=id,
        owner_id=owner_id,
        owner=owner,
        status=status,
        original_zip_path=original_zip_path,
        slug=slug,
        cover_path=None,
        error_message=None,
    )


@pytest.fixture
def kit_repo():
    return AsyncMock()


@pytest.fixture
def node_repo():
    return AsyncMock()


@pytest.fixture
def storage():
    s = AsyncMock()
    s.get_url = AsyncMock(side_effect=lambda path: f"https://cdn.example.com/{path}")
    return s


@pytest.fixture
def arq_pool():
    return AsyncMock()


@pytest.fixture
def kit_service(kit_repo, node_repo, storage, arq_pool):
    return KitService(kit_repo, node_repo, storage, arq_pool)


class TestOwnershipChecks:
    async def test_confirm_kit_upload_fails_for_non_owner(self, kit_service, kit_repo):
        kit = make_kit(owner_id=1)
        kit_repo.get_by_id.return_value = kit

        with pytest.raises(NotKitOwner):
            await kit_service.confirm_kit_upload(kit_id=1, requester_id=999)

    async def test_update_kit_fails_for_non_owner(self, kit_service, kit_repo):
        kit = make_kit(owner_id=1)
        kit_repo.get_by_slug.return_value = kit

        with pytest.raises(NotKitOwner):
            await kit_service.update_kit(slug="my-kit-abc123", requester_id=999, title="Hacked title")

        kit_repo.update_fields.assert_not_called()

    async def test_delete_kit_fails_for_non_owner(self, kit_service, kit_repo, storage):
        kit = make_kit(owner_id=1)
        kit_repo.get_by_slug.return_value = kit

        with pytest.raises(NotKitOwner):
            await kit_service.delete_kit(slug="my-kit-abc123", requester_id=999)

        kit_repo.delete.assert_not_called()
        storage.delete_async.assert_not_called()

    async def test_delete_kit_succeeds_for_owner(self, kit_service, kit_repo, storage):
        kit = make_kit(owner_id=1, id=42)
        kit_repo.get_by_slug.return_value = kit

        await kit_service.delete_kit(slug="my-kit-abc123", requester_id=1)

        storage.delete_async.assert_awaited_once_with(kit.original_zip_path)
        storage.delete_prefix.assert_awaited_once_with("kits/42/")
        kit_repo.delete.assert_awaited_once_with(42)

    async def test_init_cover_upload_fails_for_non_owner(self, kit_service, kit_repo):
        kit = make_kit(owner_id=1)
        kit_repo.get_by_id.return_value = kit

        with pytest.raises(NotKitOwner):
            await kit_service.init_cover_upload(kit_id=1, requester_id=999)

    async def test_confirm_cover_upload_fails_for_non_owner(self, kit_service, kit_repo):
        kit = make_kit(owner_id=1)
        kit_repo.get_by_id.return_value = kit

        with pytest.raises(NotKitOwner):
            await kit_service.confirm_cover_upload(kit_id=1, requester_id=999, object_key="kits/1/cover.jpg")


class TestKitReadinessGuards:
    async def test_get_kit_tree_fails_if_kit_not_ready(self, kit_service, kit_repo):
        kit = make_kit(status=KitStatus.PROCESSING)
        kit_repo.get_by_slug.return_value = kit

        with pytest.raises(KitNotReady):
            await kit_service.get_kit_tree(slug="my-kit-abc123")

    async def test_get_kit_tree_succeeds_if_ready(self, kit_service, kit_repo, node_repo):
        kit = make_kit(status=KitStatus.READY)
        kit_repo.get_by_slug.return_value = kit
        node_repo.get_flat_nodes.return_value = []

        result_kit, tree = await kit_service.get_kit_tree(slug="my-kit-abc123")

        assert result_kit is kit
        assert tree == []

    async def test_get_kit_for_download_fails_if_not_ready(self, kit_service, kit_repo):
        kit = make_kit(status=KitStatus.PENDING)
        kit_repo.get_by_slug.return_value = kit

        with pytest.raises(KitNotReady):
            await kit_service.get_kit_for_download(slug="my-kit-abc123")

        kit_repo.increment_downloads.assert_not_called()

    async def test_get_kit_for_download_increments_counter_when_ready(self, kit_service, kit_repo):
        kit = make_kit(status=KitStatus.READY, id=7)
        kit_repo.get_by_slug.return_value = kit

        result = await kit_service.get_kit_for_download(slug="my-kit-abc123")

        assert result is kit
        kit_repo.increment_downloads.assert_awaited_once_with(7)

    async def test_get_kit_for_download_fails_if_failed_status(self, kit_service, kit_repo):
        kit = make_kit(status=KitStatus.FAILED)
        kit_repo.get_by_slug.return_value = kit

        with pytest.raises(KitNotReady):
            await kit_service.get_kit_for_download(slug="my-kit-abc123")


class TestConfirmKitUpload:
    async def test_confirm_upload_rejects_oversized_file(self, kit_service, kit_repo, storage, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "MAX_ZIP_SIZE_MB", 1)  
        kit = make_kit(owner_id=1, id=1)
        kit_repo.get_by_id.return_value = kit
        storage.head_object.return_value = {"ContentLength": 2 * 1024 * 1024}

        with pytest.raises(ArchiveTooLarge):
            await kit_service.confirm_kit_upload(kit_id=1, requester_id=1)

        storage.delete_async.assert_awaited_once_with(kit.original_zip_path)
        kit_repo.mark_failed.assert_awaited_once()

    async def test_confirm_upload_succeeds_within_size_limit(
        self, kit_service, kit_repo, storage, arq_pool, monkeypatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "MAX_ZIP_SIZE_MB", 500)
        kit = make_kit(owner_id=1, id=1)
        kit_repo.get_by_id.return_value = kit
        storage.head_object.return_value = {"ContentLength": 1024}

        await kit_service.confirm_kit_upload(kit_id=1, requester_id=1)

        kit_repo.update_size.assert_awaited_once_with(1, 1024)
        arq_pool.enqueue_job.assert_awaited_once_with("process_kit", 1)

    async def test_confirm_upload_fails_if_object_missing_in_storage(self, kit_service, kit_repo, storage):
        kit = make_kit(owner_id=1, id=1)
        kit_repo.get_by_id.return_value = kit
        storage.head_object.side_effect = FileNotFoundError()

        with pytest.raises(UploadNotFound):
            await kit_service.confirm_kit_upload(kit_id=1, requester_id=1)

    async def test_confirm_upload_fails_on_client_error_from_s3(self, kit_service, kit_repo, storage):
        kit = make_kit(owner_id=1, id=1)
        kit_repo.get_by_id.return_value = kit
        storage.head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
        )

        with pytest.raises(UploadNotFound):
            await kit_service.confirm_kit_upload(kit_id=1, requester_id=1)


class TestSlugGeneration:
    def test_slug_is_url_safe_and_unique_per_call(self, kit_service):
        slug1 = kit_service._generate_slug("My Awesome Kit!!!")
        slug2 = kit_service._generate_slug("My Awesome Kit!!!")

        assert slug1 != slug2  
        assert " " not in slug1
        assert "!" not in slug1
        assert slug1.startswith("my-awesome-kit")

    def test_slug_handles_non_latin_title(self, kit_service):
        slug = kit_service._generate_slug("Ударная установка")
        assert slug  
        assert slug.count("-") >= 1
