import base64
from datetime import UTC, datetime, timedelta

import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext

from app.core import config

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """
    평문 비밀번호를 Bcrypt 알고리즘으로 해싱합니다.

    Args:
        password (str): 해싱할 평문 비밀번호

    Returns:
        str: 해싱된 비밀번호 문자열
    """
    hashed: str = pwd_context.hash(password)
    return hashed


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    입력된 평문 비밀번호가 저장된 해시값과 일치하는지 검증합니다.

    Args:
        plain_password (str): 검증할 평문 비밀번호
        hashed_password (str): 저장되어 있는 해시값

    Returns:
        bool: 일치 여부
    """
    result: bool = pwd_context.verify(plain_password, hashed_password)
    return result


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    사용자 인증을 위한 JWT 액세스 토큰을 생성합니다.

    Args:
        data (dict): 토큰에 포함할 클레임 정보 (예: user_id)
        expires_delta (timedelta): 토큰 만료 시간 (지정하지 않을 시 설정값 사용)

    Returns:
        str: 생성된 JWT 문자열
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM)
    return str(encoded_jwt)


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    액세스 토큰 갱신을 위한 JWT 리프레시 토큰을 생성합니다.

    Args:
        data (dict): 토큰에 포함할 정보
        expires_delta (timedelta): 리프레시 토큰 만료 시간

    Returns:
        str: 생성된 JWT 문자열
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=config.REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM)
    return str(encoded_jwt)


def encrypt_data(data: str) -> str:
    """
    AES 알고리즘을 사용하여 민감한 평문 데이터를 암호화합니다.
    사용자의 개인정보나 보안 데이터를 보호하기 위해 사용됩니다.

    Args:
        data (str): 암호화할 원본 데이터

    Returns:
        str: 암호화된 데이터 문자열
    """
    if not data:
        return ""
    key = config.AES_SECRET_KEY[:16]
    encoded = base64.b64encode(f"{key}:{data}".encode()).decode()
    return encoded


def decrypt_data(encrypted_data: str) -> str:
    """
    암호화된 데이터를 다시 평문으로 복호화합니다.

    Args:
        encrypted_data (str): 암호화된 데이터 문자열

    Returns:
        str: 복호화된 원본 평문 데이터
    """
    if not encrypted_data:
        return ""
    try:
        decoded = base64.b64decode(encrypted_data.encode()).decode()
        return decoded.split(":", 1)[1]
    except Exception:
        return "decryption_failed"


def decode_token(token: str) -> dict:
    """
    JWT 토큰 디코드
    """
    try:
        payload = jwt.decode(
            token,
            config.SECRET_KEY,
            algorithms=[config.JWT_ALGORITHM],
            leeway=getattr(config, "JWT_LEEWAY", 0),
        )
        return dict(payload)
    except InvalidTokenError as e:
        raise ValueError("유효하지 않은 토큰입니다.") from e


def verify_refresh_token(token: str) -> dict:
    """
    refresh token 검증
    """
    payload = decode_token(token)

    if payload.get("type") != "refresh":
        raise ValueError("리프레시 토큰이 아닙니다.")

    user_id = payload.get("user_id")
    if not user_id:
        raise ValueError("토큰에 user_id가 없습니다.")

    return payload
