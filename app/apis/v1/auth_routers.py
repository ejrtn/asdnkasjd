import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from fastapi.responses import ORJSONResponse as Response
from fastapi.security import OAuth2PasswordRequestForm

from app.core import config
from app.dtos.users import (
    KakaoAuthUrlResponse,
    LoginRequest,
    LoginResponse,
    NaverAuthUrlResponse,
    SocialLoginRequest,
    SocialLoginResponse,
)
from app.services.users import UserManageService

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/login", response_model=LoginResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: Annotated[UserManageService, Depends(UserManageService)],
) -> JSONResponse:
    """
    [USER] 로그인 (이메일/비밀번호) -> access_token 발급
    """
    login_data = LoginRequest(id=form_data.username, password=form_data.password)
    tokens = await user_service.login(login_data)

    response = JSONResponse(
        content={"access_token": tokens["access_token"], "token_type": tokens["token_type"], "id": tokens["id"]},
        status_code=status.HTTP_200_OK,
    )
    response.set_cookie("access_token", tokens["access_token"], httponly=False, samesite="lax")
    return response


@auth_router.get("/kakao/authorize", response_model=KakaoAuthUrlResponse)
async def kakao_authorize() -> Response:
    """
    [USER] 카카오 소셜 로그인 시작.
    프론트는 반환된 auth_url로 리다이렉트하여 인가코드(code)를 획득
    """
    kakao_client_id = config.KAKAO_CLIENT_ID
    redirect_uri = config.KAKAO_REDIRECT_URI
    auth_url = (
        f"https://kauth.kakao.com/oauth/authorize?response_type=code"
        f"&client_id={kakao_client_id}&redirect_uri={redirect_uri}"
    )
    return Response(content={"auth_url": auth_url}, status_code=status.HTTP_200_OK)


@auth_router.get("/kakao/callback", response_model=SocialLoginResponse)
async def kakao_callback(code: str, user_service: Annotated[UserManageService, Depends(UserManageService)]) -> Response:
    """
    [USER] 카카오 로그인 콜백. service access_token 발급.
    """
    # Using existing service logic for demo data mapping

    social_data = SocialLoginRequest(
        id="kakao_user@kakao.com",
        name="카카오사용자",
        nickname="kakao_user_456",
        phone_number="01098765432",
        social_id="kakao_unique_id_abc",
        provider="kakao",
    )
    tokens = await user_service.social_login(social_data)

    return Response(
        content={
            "user_id": tokens["id"],
            "is_new_user": tokens.get("is_new_user", False),
            "access_token": tokens["access_token"],
        },
        status_code=status.HTTP_200_OK,
    )


@auth_router.get("/naver/authorize", response_model=NaverAuthUrlResponse)
async def naver_authorize() -> Response:
    """
    [USER] 네이버 소셜 로그인 시작.
    프론트는 반환된 auth_url로 리다이렉트하여 인가코드(code)를 획득
    """
    naver_client_id = config.NAVER_CLIENT_ID
    redirect_uri = config.NAVER_REDIRECT_URI
    # state parameter is recommended for Naver to prevent CSRF

    state = str(uuid.uuid4())[:8]
    auth_url = (
        f"https://nid.naver.com/oauth2.0/authorize?response_type=code"
        f"&client_id={naver_client_id}&redirect_uri={redirect_uri}&state={state}"
    )
    return Response(content={"auth_url": auth_url}, status_code=status.HTTP_200_OK)


@auth_router.get("/naver/callback", response_model=SocialLoginResponse)
async def naver_callback(
    code: str, user_service: Annotated[UserManageService, Depends(UserManageService)], state: str | None = None
) -> Response:
    """
    [USER] 네이버 로그인 콜백. service access_token 발급.
    """

    # Mocking Naver user data for implementation demonstration
    social_data = SocialLoginRequest(
        id="naver_user@naver.com",
        name="네이버사용자",
        nickname="naver_user_789",
        phone_number="01012345678",
        social_id="naver_unique_id_xyz",
        provider="naver",
    )
    tokens = await user_service.social_login(social_data)

    return Response(
        content={
            "user_id": tokens["id"],
            "is_new_user": tokens.get("is_new_user", False),
            "access_token": tokens["access_token"],
        },
        status_code=status.HTTP_200_OK,
    )
