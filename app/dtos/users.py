from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field

from app.dtos.base import BaseSerializerModel
from app.validators.user_validators import (
    validate_password,
    validate_phone_number,
)


# 회원가입 요청
class SignUpRequest(BaseModel):
    id: Annotated[
        EmailStr,
        Field(max_length=40),
    ]
    password: Annotated[str, Field(min_length=8), AfterValidator(validate_password)]
    name: Annotated[str, Field(max_length=20)]
    nickname: Annotated[str, Field(max_length=20)]
    birthday: Annotated[str, Field(max_length=10)]
    gender: Annotated[str, Field(max_length=10)]
    phone_number: Annotated[str, AfterValidator(validate_phone_number)]
    alarm_tf: bool
    is_terms_agreed: bool
    is_privacy_agreed: bool
    is_marketing_agreed: bool
    is_alarm_agreed: bool
    social_signup_token: str | None = None


# 회원가입 응답
class SignUpResponse(BaseModel):
    id: str
    access_token: str


class IdDuplicationRequest(BaseModel):
    id: str


# 로그인 요청 (OAuth2 Password Bearer용 - form_data로 처리되지만 DTO로도 정의 가능)
class LoginRequest(BaseModel):
    id: EmailStr
    password: Annotated[str, Field(..., description="패스워드")]


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: str | None = None


class LoginResponse(Token):
    id: str
    refresh_token: str | None = None  # 쿠키로 내려줄 수도 있고 바디에 포함할 수도 있음


class TokenRefreshResponse(BaseModel):
    access_token: str


# 소셜 로그인 요청
class SocialLoginRequest(BaseModel):
    id: EmailStr
    name: str
    nickname: str
    phone_number: str
    social_id: str
    provider: str
    birthday: str
    gender: str


class SocialLoginApiRequest(BaseModel):
    code: str
    state: str | None = None


class SocialLoginApiResponse(BaseModel):
    status: str
    access_token: str | None = None  # login_success 시 제공
    social_signup_token: str | None = None  # signup_required 시 제공
    profile: SocialLoginRequest | None = None  # signup_required 시 제공


# 구글 인가 URL 응답
class GoogleAuthUrlResponse(BaseModel):
    auth_url: str


# 네이버 인가 URL 응답
class NaverAuthUrlResponse(BaseModel):
    auth_url: str


# 정보 조회 응답
class UserMeResponse(BaseSerializerModel):
    id: EmailStr
    nickname: str
    name: str
    phone_number: str
    birthday: str
    gender: str
    chronic_diseases: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    alarm_tf: bool
    is_terms_agreed: bool
    is_privacy_agreed: bool
    is_marketing_agreed: bool
    is_alarm_agreed: bool
    provider: str | None = None

    class Config:
        from_attributes = True


# 정보 수정 요청
class UserUpdateRequest(BaseModel):
    nickname: Annotated[str | None, Field(None, min_length=2, max_length=40)]
    phone_number: Annotated[str | None, AfterValidator(validate_phone_number)] = None
    birthday: Annotated[str, Field(max_length=10)]
    gender: Annotated[str, Field(max_length=10)]
    alarm_tf: bool
    is_marketing_agreed: bool
    is_alarm_agreed: bool


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="현재 비밀번호")
    new_password: str = Field(..., description="새 비밀번호")


class FcmTokenUpdateRequest(BaseModel):
    fcm_token: str = Field(..., description="FCM 토큰")
