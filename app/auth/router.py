import secrets

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse

from app.auth.deps import get_auth_service
from app.auth.exceptions import InvalidToken
from app.auth.oauth import oauth
from app.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenPair,
    UserCreate,
    VerifyEmailRequest,
)
from app.auth.service import AuthService
from app.core.config import settings
from app.core.limiter import limiter
from app.users.schemas import UserRead

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register(
    request: Request,
    data: UserCreate,
    service: AuthService = Depends(get_auth_service),
):
    user = await service.register(data.email, data.username, data.password)
    return user


@router.post("/login", response_model=TokenPair)
@limiter.limit("5/minute")
async def login(
    request: Request,
    data: LoginRequest,
    service: AuthService = Depends(get_auth_service),
):
    return await service.login(data.email, data.password)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    data: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
):
    return await service.refresh(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
):
    await service.logout(data.refresh_token)


@router.get("/google/login")
@limiter.limit("10/minute")
async def google_login(request: Request):
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    request.session["nonce"] = secrets.token_urlsafe(16)
    return await oauth.google.authorize_redirect(
        request, redirect_uri, nonce=request.session["nonce"]
    )


@router.get("/google/callback")
async def google_callback(
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    token = await oauth.google.authorize_access_token(request)
    nonce = request.session.get("nonce")
    user_info = await oauth.google.parse_id_token(token, nonce=nonce)

    if not user_info or not user_info.get("email"):
        raise InvalidToken()

    tokens = await service.login_with_google(
        google_id=user_info["sub"], email=user_info["email"]
    )

    redirect_url = (
        f"{settings.FRONTEND_URL}/auth/google/callback"
        f"#access_token={tokens.access_token}&refresh_token={tokens.refresh_token}"
    )
    return RedirectResponse(url=redirect_url)


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def verify_email(
    request: Request,
    data: VerifyEmailRequest,
    service: AuthService = Depends(get_auth_service),
):
    await service.verify_email(data.email, data.code)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    service: AuthService = Depends(get_auth_service),
):
    await service.forgot_password(data.email)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    service: AuthService = Depends(get_auth_service),
):
    await service.reset_password(data.email, data.code, data.new_password)


@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("3/minute")
async def resend_verification(
    request: Request,
    data: ResendVerificationRequest,
    service: AuthService = Depends(get_auth_service),
):
    await service.resend_verification_code(data.email)
