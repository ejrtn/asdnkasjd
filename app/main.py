import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from tortoise import Tortoise  # 추가됨

from app.apis.v1 import api_v1_router
from app.core.http_client import http_client
from app.db.databases import TORTOISE_ORM, initialize_tortoise
from app.utils.default_data import DefaultData

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

logger = logging.getLogger("seed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    # 1. HTTP Client 초기화
    http_client.init_client()

    # 2. DB 초기화 로직 (매번 전체 드롭 후 재생성하여 스키마 동기화)
    logger.warning("🔨🔨🔨 [lifespan] DB Reset process starting...")
    try:
        # [A] 기존 DB 접속 및 전체 드롭
        await Tortoise.init(config=TORTOISE_ORM)
        await Tortoise._drop_databases()
        logger.warning("✅ 기존 데이터베이스 및 테이블 삭제 완료.")

        # [B] DB 다시 생성 및 최신 모델 반영 (is_valid 등 최신 필드 생성)
        # _create_db=True 옵션이 삭제된 ai_health 데이터베이스를 다시 만듭니다.
        await Tortoise.init(config=TORTOISE_ORM, _create_db=True)
        await Tortoise.generate_schemas()
        logger.warning("✅ 최신 스키마로 DB 테이블 생성 완료.")

    except Exception as e:
        logger.error(f"❌ DB Reset failed: {e}")

    # 3. 기본 데이터 생성
    logger.warning("🔥🔥🔥 [lifespan] seed_default_data starting")
    try:
        await DefaultData().create_default_data()
        logger.warning("✅✅✅ Default data population completed successfully.")
    except Exception:
        logger.exception("⚠️⚠️⚠️ Default data population failed")

    yield

    # --- Shutdown ---
    # 1. HTTP Client 종료
    await http_client.close_client()
    # 2. DB 연결 종료
    await Tortoise.close_connections()
    logger.warning("👋 [lifespan] server resources closed")


app = FastAPI(
    default_response_class=ORJSONResponse,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
initialize_tortoise(app)

# Tortoise-ORM의 SQL 로그를 활성화
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("tortoise.db_client").setLevel(logging.DEBUG)

# [추가된 기능] 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="app/static"), name="static")
uploads_dir = os.path.join(os.path.dirname(__file__), "../uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
templates = Jinja2Templates(directory="app/templates")


def _is_logged_in(request: Request) -> bool:
    # 프론트엔드 authGuard가 세션 관리를 담당하므로 서버 측 체크 최소화
    # 공개 페이지에서만 사용 (로그인 상태면 대시보드로 리다이렉트)
    return bool(request.cookies.get("access_token"))


def require_login(request: Request):
    # 서버 측 로그인 체크 제거 - 프론트엔드 authGuard가 처리
    # API 레벨에서는 JWT Bearer 토큰으로 인증 처리
    return None


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    """
    랜딩 페이지. 프론트엔드에서 localStorage 기준으로 대시보드 이동 처리.
    """
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    대시보드. 프론트엔드 authGuard가 세션 관리를 처리.
    """
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/signup", response_class=HTMLResponse)
async def read_join(request: Request):
    return templates.TemplateResponse("join.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def read_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/mypage", response_class=HTMLResponse)
async def read_mypage(request: Request):
    """
    사용자 마이페이지. 프론트엔드 authGuard가 세션 관리를 처리.
    """
    return templates.TemplateResponse("mypage.html", {"request": request})


@app.get("/find-account", response_class=HTMLResponse)
async def read_find_id_pw(request: Request):
    """
    아이디 및 비밀번호 찾기 페이지를 반환합니다.
    """
    return templates.TemplateResponse("find_account.html", {"request": request})


@app.get("/guide", response_class=HTMLResponse)
async def read_guide(request: Request):
    """
    생활 안내 가이드 페이지. 프론트엔드 authGuard가 세션 관리를 처리.
    """
    return templates.TemplateResponse("guide.html", {"request": request})


@app.get("/alarm", response_class=HTMLResponse)
async def read_alarm(request: Request):
    """
    복용 알람 페이지. 프론트엔드 authGuard가 세션 관리를 처리.
    """
    return templates.TemplateResponse("alarm.html", {"request": request})


@app.get("/prescription-upload", response_class=HTMLResponse)
async def read_prescription_upload(request: Request):
    """
    처방전 및 약물 업로드 페이지. 프론트엔드 authGuard가 세션 관리를 처리.
    """
    return templates.TemplateResponse("prescription_upload.html", {"request": request})


@app.get("/health-profile", response_class=HTMLResponse)
async def read_health_profile(request: Request):
    """
    건강 정보 통합 관리 페이지. 프론트엔드 authGuard가 세션 관리를 처리.
    """
    return templates.TemplateResponse("health_profile_save.html", {"request": request})


@app.get("/blood-pressure", response_class=HTMLResponse)
async def read_blood_pressure(request: Request):
    """
    혈압 기록 페이지. 프론트엔드 authGuard가 세션 관리를 처리.
    """
    return templates.TemplateResponse("blood_pressure_save.html", {"request": request})


@app.get("/blood-sugar", response_class=HTMLResponse)
async def read_blood_sugar(request: Request):
    """
    혈당 기록 페이지. 프론트엔드 authGuard가 세션 관리를 처리.
    """
    return templates.TemplateResponse("blood_sugar_save.html", {"request": request})


app.include_router(api_v1_router)
