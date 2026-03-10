import os
import uuid
import zoneinfo
from dataclasses import field
from enum import StrEnum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(StrEnum):
    """
    애플리케이션의 실행 환경(로컬, 개발, 운영)을 정의하는 열거형 클래스입니다.
    """

    LOCAL = "local"
    DEV = "dev"
    PROD = "prod"


class Config(BaseSettings):
    """
    애플리케이션의 모든 환경 변수 및 설정을 관리하는 클래스입니다.
    Pydantic Settings를 기반으로 .env 파일 및 시스템 환경 변수를 로드합니다.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    ENV: Env = Env.LOCAL
    SECRET_KEY: str = f"default-secret-key{uuid.uuid4().hex}"
    TIMEZONE: zoneinfo.ZoneInfo = field(default_factory=lambda: zoneinfo.ZoneInfo("Asia/Seoul"))
    TEMPLATE_DIR: str = os.path.join(Path(__file__).resolve().parent.parent, "templates")

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_NAME: str = ""
    DB_CONNECT_TIMEOUT: int = 5
    DB_CONNECTION_POOL_MAXSIZE: int = 10

    SMTP_USER: str = ""  # .env의 SMTP_USER와 매칭
    SMTP_PASSWORD: str = ""  # .env의 SMTP_PASSWORD와 매칭
    SMTP_HOST: str = "smtp.naver.com"
    SMTP_PORT: int = 587
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    MAIL_FROM: str = ""

    COOKIE_DOMAIN: str = "localhost"

    # OpenAI API
    OPENAI_API_KEY: str = ""

    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "cloud9care"
    MONGODB_CHAT_COLLECTION: str = "chat_messages"

    # Chat Settings
    CHAT_MODEL: str = "gpt-4o-mini"
    CHAT_HISTORY_LIMIT: int = 8
    RESET_DB_ON_STARTUP: bool = False

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 30 * 24 * 60  # 자동로그인 체크 시 30일 유지
    REFRESH_TOKEN_EXPIRE_MINUTES_SHORT: int = 60  # 자동로그인 체크 안 할 시 60분 유지
    JWT_LEEWAY: int = 5

    # Naver Social Login
    NAVER_CLIENT_ID: str = ""
    NAVER_CLIENT_SECRET: str = ""
    NAVER_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/naver/callback"

    # Google Social Login
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Security & Encryption
    AES_SECRET_KEY: str = f"aes-default-secret-{uuid.uuid4().hex[:16]}"

    # Firebase FCM
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_CLIENT_EMAIL: str = ""
    FIREBASE_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""

    # Naver Clova OCR
    CLOVA_OCR_INVOKE_URL: str = ""
    CLOVA_OCR_SECRET_KEY: str = ""

    UPLOAD_DIR: str = ""


config = Config()
