from app.core.exceptions import AppException


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


class SamePassword(AppException):
    status_code = 400
    detail = "New password must be different from the current password"
