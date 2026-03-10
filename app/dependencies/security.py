from typing import Annotated

import jwt  # type: ignore[import-untyped, import-not-found]
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError  # type: ignore[import-untyped, import-not-found]

from app.core import config
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.common import redis_client

# OAuth2PasswordBearer specifies that the client must send the token in an Authorization header with Bearer scheme.
# The tokenUrl points to the login endpoint (relative to the API root).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_request_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """
    HTTP 요청 헤더의 Bearer 토큰을 검증하고 현재 인증된 사용자를 반환하는 종속성 함수입니다.
    JWT 유효성 검사 및 Redis 세션 토큰 대조를 통해 보완적인 보안 확인을 거칩니다.

    Args:
        token (str): 요청 헤더에서 추출된 액세스 토큰

    Returns:
        User: 인증에 성공한 사용자 환경 정보

    Raises:
        HTTPException: 토큰이 유효하지 않거나 세션이 만료된 경우 401 에러 발생
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="로그인이 필요하거나 세션이 만료되었습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
        user_email: str = payload.get("user_id")
        token_type: str = payload.get("type")

        if user_email is None or token_type != "access":
            raise credentials_exception

        # Redis 세션 확인 (중복 로그인 방지 및 세션 강제 종료 대응)
        stored_token = await redis_client.get(f"session:{user_email}")

        # 디버그 로그 (임시)
        print("DEBUG user_email:", user_email)
        print("DEBUG token type:", type(token), "value:", token[:30] if token else None)
        print("DEBUG stored_token raw type:", type(stored_token), "value:", stored_token[:30] if stored_token else None)

        # bytes 타입 처리
        if isinstance(stored_token, bytes):
            stored_token = stored_token.decode("utf-8")

        print(
            "DEBUG stored_token decoded type:",
            type(stored_token),
            "value:",
            stored_token[:30] if stored_token else None,
        )

        if not stored_token or stored_token != token:
            raise credentials_exception

    except InvalidTokenError as err:
        raise credentials_exception from err

    user = await UserRepository().get_by_id(user_email)
    if user is None:
        raise credentials_exception

    return user


async def get_optional_user(request: Request) -> User | None:
    """
    인증이 선택적인 엔드포인트를 위한 종속성 함수입니다.
    토큰이 없거나 유효하지 않아도 에러를 발생시키지 않고 None을 반환합니다.
    (데모용: OAuth2PasswordBearer의 strict 체크를 방지하기 위해 헤더를 직접 확인)
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    try:
        return await get_request_user(token)
    except Exception:
        return None
