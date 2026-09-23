from app.core.exceptions import AppException


class UploadTokenInvalid(AppException):
    status_code = 400
    detail = "Upload token is invalid or expired"
