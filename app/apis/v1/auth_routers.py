import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.responses import ORJSONResponse as Response
from fastapi.security import OAuth2PasswordRequestForm

from app.core import config
from app.dtos.users import (
    GoogleAuthUrlResponse,
    LoginRequest,
    LoginResponse,
    NaverAuthUrlResponse,
    SocialLoginApiRequest,
    SocialLoginApiResponse,
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


@auth_router.get("/google/authorize", response_model=GoogleAuthUrlResponse)
async def google_authorize() -> Response:
    """
    [USER] 구글 소셜 로그인 시작.
    프론트는 반환된 auth_url로 리다이렉트하여 인가코드(code)를 획득
    """
    google_client_id = config.GOOGLE_CLIENT_ID
    redirect_uri = config.GOOGLE_REDIRECT_URI
    scope = "openid email profile"
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code"
        f"&client_id={google_client_id}&redirect_uri={redirect_uri}&scope={scope}"
    )
    return Response(content={"auth_url": auth_url}, status_code=status.HTTP_200_OK)


@auth_router.post("/google/login", response_model=SocialLoginApiResponse)
async def google_login_api(
    request_data: SocialLoginApiRequest,
    user_service: Annotated[UserManageService, Depends(UserManageService)],
) -> Response:
    """
    [USER] 구글 소셜 로그인 처리 (API)
    인가 코드를 받아 신규 가입 필요 여부를 반환합니다.
    """
    api_response, refresh_token = await user_service.google_login(request_data.code)

    response = Response(content=api_response.model_dump(), status_code=status.HTTP_200_OK)

    if api_response.status == "login_success" and refresh_token:
        response.set_cookie(
            "refresh_token",
            refresh_token,
            httponly=True,
            samesite="lax",
            path="/",
            max_age=config.REFRESH_TOKEN_EXPIRE_MINUTES_SHORT * 60,
        )

    return response


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
        f"&client_id={naver_client_id}&redirect_uri={redirect_uri}&state={state}&auth_type=reprompt"
    )
    return Response(content={"auth_url": auth_url}, status_code=status.HTTP_200_OK)


@auth_router.post("/naver/login", response_model=SocialLoginApiResponse)
async def naver_login_api(
    request_data: SocialLoginApiRequest, user_service: Annotated[UserManageService, Depends(UserManageService)]
) -> Response:
    """
    [USER] 네이버 소셜 로그인 처리 (API)
    인가 코드를 받아 신규 가입 필요 여부를 반환합니다.
    """
    api_response, refresh_token = await user_service.naver_login(request_data.code, request_data.state)

    response = Response(content=api_response.model_dump(), status_code=status.HTTP_200_OK)

    if api_response.status == "login_success" and refresh_token:
        response.set_cookie(
            "refresh_token",
            refresh_token,
            httponly=True,
            samesite="lax",
            path="/",
            max_age=config.REFRESH_TOKEN_EXPIRE_MINUTES_SHORT * 60,
        )

    return response


def get_social_callback_html(provider: str) -> str:
    """소셜 로그인 팝업용 HTML 스피너. 코드를 받아 API를 호출하고 부모창에 결과를 보냅니다."""
    return f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>로그인 처리 중...</title>
        <style>
            body {{ display:flex; justify-content:center; align-items:center; height:100vh; background:#f9fafb; font-family:sans-serif; overflow: hidden; }}
            .spinner {{ width: 40px; height: 40px; border: 4px solid #e5e7eb; border-top-color: #4f46e5; border-radius: 50%; animation: spin 1s linear infinite; }}
            @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
            .app-toast {{ position: fixed; top: 20px; right: 20px; z-index: 9999; display: none; }}
            .app-toast.show {{ display: block; animation: slideIn 0.3s ease-out; }}
            @keyframes slideIn {{ from {{ transform: translateX(100%); opacity: 0; }} to {{ transform: translateX(0); opacity: 1; }} }}
            .app-toast-inner {{ background: white; border-radius: 12px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05); border: 1px solid #e5e7eb; display: flex; align-items: center; padding: 12px 16px; min-width: 280px; }}
            .app-toast-badge {{ font-size: 20px; margin-right: 12px; }}
            .app-toast-content {{ flex: 1; }}
            .app-toast-title {{ font-size: 13px; font-weight: 700; color: #111827; }}
            .app-toast-message {{ font-size: 13px; color: #4b5563; margin-top: 2px; }}
        </style>
    </head>
    <body>
        <div style="text-align:center;">
            <div class="spinner"></div>
            <p style="margin-top:20px; color:#4b5563;">로그인 처리 중입니다...</p>
        </div>

        <div id="app-toast" class="app-toast">
            <div class="app-toast-inner">
                <div class="app-toast-badge" id="app-toast-badge">⚠️</div>
                <div class="app-toast-content">
                    <div class="app-toast-title" id="app-toast-title">안내</div>
                    <div class="app-toast-message" id="app-toast-message">알림 메시지</div>
                </div>
            </div>
        </div>

        <script>
            function showLocalToast(message, type = 'warn', title = '알림') {{
                const toast = document.getElementById('app-toast');
                const badge = document.getElementById('app-toast-badge');
                const titleEl = document.getElementById('app-toast-title');
                const msgEl = document.getElementById('app-toast-message');
                
                titleEl.textContent = title;
                msgEl.textContent = message;
                badge.textContent = type === 'success' ? '✅' : (type === 'warn' ? '⚠️' : 'ℹ️');
                
                toast.classList.add('show');
                return new Promise(resolve => setTimeout(resolve, 2000));
            }}

            async function processLogin() {{
                const urlParams = new URLSearchParams(window.location.search);
                const code = urlParams.get('code');
                const state = urlParams.get('state');

                if (!code) {{
                    await showLocalToast("인증 코드가 없습니다.", "warn", "로그인 실패");
                    window.close();
                    return;
                }}

                try {{
                    const response = await fetch('/api/v1/auth/{provider}/login', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ code: code, state: state }})
                    }});

                    const data = await response.json();

                    if (window.opener) {{
                        window.opener.postMessage(data, '*');
                        window.close();
                    }} else {{
                        await showLocalToast("부모 창을 찾을 수 없습니다.", "warn", "로그인 실패");
                        window.close();
                    }}
                }} catch (e) {{
                    await showLocalToast("로그인 처리 중 오류가 발생했습니다.", "warn", "오류");
                    window.close();
                }}
            }}
            window.onload = processLogin;
        </script>
    </body>
    </html>
    """


@auth_router.get("/google/callback", response_class=HTMLResponse)
async def google_callback() -> HTMLResponse:
    """
    [USER] 구글 로그인 콜백 페이지 (클라이언트 팝업).
    이 페이지가 브라우저에 렌더링되어 POST API를 호출합니다.
    """
    return HTMLResponse(content=get_social_callback_html("google"), status_code=status.HTTP_200_OK)


@auth_router.get("/naver/callback", response_class=HTMLResponse)
async def naver_callback() -> HTMLResponse:
    """
    [USER] 네이버 로그인 콜백 페이지 (클라이언트 팝업).
    """
    return HTMLResponse(content=get_social_callback_html("naver"), status_code=status.HTTP_200_OK)
