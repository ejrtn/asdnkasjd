import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, ORJSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.apis.v1 import api_v1_router
from app.db.databases import initialize_tortoise
from app.utils.default_data import DefaultData

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

app = FastAPI(
    default_response_class=ORJSONResponse, docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json"
)
initialize_tortoise(app)

logger = logging.getLogger("seed")


# startup 이벤트 함수 추가
@app.on_event("startup")
async def seed_default_data():
    logger.warning("🔥🔥🔥 [startup] seed_default_data called")
    try:
        await DefaultData().create_default_data()
        logger.warning("✅✅✅ Default data population completed successfully.")
    except Exception:
        logger.exception("⚠️⚠️⚠️ Default data population failed")


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
    return bool(request.cookies.get("access_token"))


def require_login(request: Request):
    if not _is_logged_in(request):
        return RedirectResponse(url="/", status_code=302)
    return None


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    """
    랜딩 페이지. 로그인 상태면 대시보드로 리다이렉트.
    """
    if _is_logged_in(request):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    대시보드. 로그인한 사용자만 접근 가능.
    """
    r = require_login(request)
    if r:
        return r
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/signup", response_class=HTMLResponse)
async def read_join(request: Request):
    if _is_logged_in(request):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("join.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def read_login(request: Request):
    if _is_logged_in(request):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/mypage", response_class=HTMLResponse)
async def read_mypage(request: Request):
    """
    사용자 마이페이지(정보 수정, 비밀번호 변경 등)를 반환합니다.
    """
    r = require_login(request)
    if r:
        return r
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
    생활 안내 가이드 페이지를 반환합니다.
    """
    r = require_login(request)
    if r:
        return r
    return templates.TemplateResponse("guide.html", {"request": request})


@app.get("/alarm", response_class=HTMLResponse)
async def read_alarm(request: Request):
    """
    복용 알람 페이지를 반환합니다.
    """
    r = require_login(request)
    if r:
        return r
    return templates.TemplateResponse("alarm.html", {"request": request})


@app.get("/prescription-upload", response_class=HTMLResponse)
async def read_prescription_upload(request: Request):
    """
    처방전 및 약물 업로드 페이지를 반환합니다.
    """
    r = require_login(request)
    if r:
        return r
    return templates.TemplateResponse("prescription_upload.html", {"request": request})


@app.get("/health-profile", response_class=HTMLResponse)
async def read_health_profile(request: Request):
    """
    건강 정보 통합 관리 페이지를 반환합니다.
    """
    r = require_login(request)
    if r:
        return r
    return templates.TemplateResponse("health_profile_save.html", {"request": request})


@app.get("/blood-pressure", response_class=HTMLResponse)
async def read_blood_pressure(request: Request):
    """
    혈압 기록 페이지를 반환합니다.
    """
    r = require_login(request)
    if r:
        return r
    return templates.TemplateResponse("blood_pressure_save.html", {"request": request})


@app.get("/blood-sugar", response_class=HTMLResponse)
async def read_blood_sugar(request: Request):
    """
    혈당 기록 페이지를 반환합니다.
    """
    r = require_login(request)
    if r:
        return r
    return templates.TemplateResponse("blood_sugar_save.html", {"request": request})


app.include_router(api_v1_router)
