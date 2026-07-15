from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    is_active: bool
    avatar_path: str | None = None


class UserPublicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    avatar_path: str | None = None


class UserUpdateEmail(BaseModel):
    email: EmailStr


class UserUpdateUsername(BaseModel):
    username: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not (3 <= len(v) <= 50):
            raise ValueError("Username must be between 3 and 50 characters long")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain letters, digits, '_' and '-'")
        return v


class UserChangePassword(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v