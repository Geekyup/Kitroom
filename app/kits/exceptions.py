from app.core.exceptions import AppException


class KitNotFound(AppException):
    status_code = 404
    detail = "Kit not found"


class KitNotReady(AppException):
    status_code = 202
    detail = "Kit is still being processed"


class KitProcessingFailed(AppException):
    status_code = 422
    detail = "Kit processing failed"


class ArchiveTooLarge(AppException):
    status_code = 413
    detail = "Archive exceeds maximum allowed size"


class TooManyFilesInArchive(AppException):
    status_code = 422
    detail = "Archive contains too many files"


class InvalidArchive(AppException):
    status_code = 422
    detail = "Archive is corrupted or has an unsupported format"


class UnsupportedAudioFormat(AppException):
    status_code = 422
    detail = "Archive contains files with unsupported audio formats"


class ZipSlipDetected(AppException):
    status_code = 422
    detail = "Archive contains unsafe file paths"


class NotKitOwner(AppException):
    status_code = 403
    detail = "You are not the owner of this kit"


class UploadNotFound(AppException):
    status_code = 404
    detail = "File not found in storage — upload incomplete or invalid key"
