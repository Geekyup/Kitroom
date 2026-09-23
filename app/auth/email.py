import resend

from app.core.config import settings

resend.api_key = settings.RESEND_API_KEY


def send_verification_email(to_email: str, code: str) -> None:
    resend.Emails.send({
        "from": settings.EMAIL_FROM,
        "to": to_email,
        "subject": "Подтверждение почты",
        "html": f"<p>Твой код подтверждения: <strong>{code}</strong></p><p>Код действителен {settings.VERIFICATION_CODE_EXPIRE_MINUTES} минут.</p>",
    })


def send_password_reset_email(to_email: str, code: str) -> None:
    resend.Emails.send({
        "from": settings.EMAIL_FROM,
        "to": to_email,
        "subject": "Восстановление пароля",
        "html": f"<p>Твой код для сброса пароля: <strong>{code}</strong></p><p>Код действителен {settings.PASSWORD_RESET_CODE_EXPIRE_MINUTES} минут. Если это был не ты — просто проигнорируй письмо.</p>",
    })