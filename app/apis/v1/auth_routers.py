from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.core import config
from app.dtos.users import (
    LoginRequest,
    LoginResponse,
)
from app.services.users import UserManageService
from app.utils.security import create_access_token, verify_refresh_token

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: Annotated[UserManageService, Depends(UserManageService)],
) -> JSONResponse:
    """
    [USER] 로그인 -> access_token + refresh_token 발급
    """
    form = await request.form()
    remember_me = str(form.get("remember_me", "")).lower() in ("true", "1", "on", "yes")

    login_data = LoginRequest(id=form_data.username, password=form_data.password)
    tokens = await user_service.login(login_data, remember_me=remember_me)

    refresh_max_age = (
        config.REFRESH_TOKEN_EXPIRE_MINUTES * 60 if remember_me else config.REFRESH_TOKEN_EXPIRE_MINUTES_SHORT * 60
    )

    response = JSONResponse(
        content={
            "access_token": tokens["access_token"],
            "token_type": tokens["token_type"],
            "id": tokens["id"],
        },
        status_code=status.HTTP_200_OK,
    )

    # 프론트 localStorage 동기화용
    response.set_cookie("access_token", tokens["access_token"], httponly=False, samesite="lax", path="/")
    response.set_cookie("user_id", str(tokens["id"]), httponly=False, samesite="lax", path="/")

    # 실제 재발급용
    response.set_cookie(
        "refresh_token",
        tokens["refresh_token"],
        httponly=True,
        samesite="lax",
        path="/",
        max_age=refresh_max_age,
    )
    return response


@auth_router.get("/token/refresh")
async def refresh_access_token(
    refresh_token: str | None = Cookie(default=None),
) -> JSONResponse:
    """
    [USER] refresh_token으로 access_token 재발급
    """
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="리프레시 토큰이 없습니다.")

    try:
        payload = verify_refresh_token(refresh_token)
        user_id = payload["user_id"]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e

    access_token = create_access_token(
        data={"user_id": user_id},
        expires_delta=timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    response = JSONResponse(
        content={
            "access_token": access_token,
            "token_type": "bearer",
        },
        status_code=status.HTTP_200_OK,
    )
    response.set_cookie("access_token", access_token, httponly=False, samesite="lax", path="/")
    return response
