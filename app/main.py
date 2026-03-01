from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.apis.v1 import api_v1_router
from app.core.logger import logging
from app.db.databases import initialize_tortoise

app = FastAPI(
    default_response_class=ORJSONResponse, docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json"
)
initialize_tortoise(app)


# Tortoise-ORM의 SQL 로그를 활성화
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("tortoise.db_client").setLevel(logging.DEBUG)

# [추가된 기능] 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    서비스의 메인 랜딩 페이지(Index)를 반환합니다.
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/signup", response_class=HTMLResponse)
async def read_join(request: Request):
    """
    회원가입 페이지를 반환합니다.
    """
    return templates.TemplateResponse("join.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def read_login(request: Request):
    """
    로그인 페이지를 반환합니다.
    """
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/mypage", response_class=HTMLResponse)
async def read_mypage(request: Request):
    """
    사용자 마이페이지(정보 수정, 비밀번호 변경 등)를 반환합니다.
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
    생활 안내 가이드 페이지를 반환합니다.
    """
    return templates.TemplateResponse("guide.html", {"request": request})


@app.get("/alarm", response_class=HTMLResponse)
async def read_alarm(request: Request):
    """
    복용 알람 페이지를 반환합니다.
    """
    return templates.TemplateResponse("alarm.html", {"request": request})


@app.get("/prescription-upload", response_class=HTMLResponse)
async def read_prescription_upload(request: Request):
    """
    처방전 및 약물 업로드 페이지를 반환합니다.
    """
    return templates.TemplateResponse("prescription_upload.html", {"request": request})


app.include_router(api_v1_router)
