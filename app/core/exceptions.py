class AppException(Exception):
    status_code: int = 400
    detail: str = "Application error"

    def __init__(self, detail: str | None = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)


# --- Auth ---

class InvalidCredentials(AppException):
    status_code = 401
    detail = "Invalid email or password"


class InvalidToken(AppException):
    status_code = 401
    detail = "Invalid token"


class TokenExpired(AppException):
    status_code = 401
    detail = "Token has expired"


class TokenRevoked(AppException):
    status_code = 401
    detail = "Token has been revoked"


class WrongTokenType(AppException):
    status_code = 401
    detail = "Wrong token type"


class InactiveUser(AppException):
    status_code = 403
    detail = "User account is inactive"


class EmailNotVerified(AppException):
    status_code = 403
    detail = "Email is not verified"


class EmailAlreadyVerified(AppException):
    status_code = 400
    detail = "Email is already verified"


class UserAlreadyExists(AppException):
    status_code = 409
    detail = "User with this email already exists"


class UsernameAlreadyExists(AppException):
    status_code = 409
    detail = "Username is already taken"


class UserNotFound(AppException):
    status_code = 404
    detail = "User not found"


class InvalidVerificationCode(AppException):
    status_code = 400
    detail = "Invalid or expired verification code"


# --- Kit lifecycle ---

class KitNotFound(AppException):
    status_code = 404
    detail = "Kit not found"


class KitNotReady(AppException):
    status_code = 202
    detail = "Kit is still being processed"


class KitProcessingFailed(AppException):
    status_code = 422
    detail = "Kit processing failed"


# --- Upload / archive validation ---

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


# --- Ownership ---

class NotKitOwner(AppException):
    status_code = 403
    detail = "You are not the owner of this kit"


class SamePassword(AppException):
    status_code = 400
    detail = "New password must be different from the current password"


class UploadNotFound(AppException):
    status_code = 404
    detail = "Файл не найден в хранилище — аплоад не завершён или ключ неверный"