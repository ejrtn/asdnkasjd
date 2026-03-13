from datetime import timedelta
from urllib.parse import quote  # 파일 상단에 추가

import httpx
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse
from passlib.context import CryptContext
from pydantic import EmailStr
from starlette import status
from tortoise.transactions import in_transaction

from app.core import config
from app.dtos.users import (
    ChangePasswordRequest,
    LoginRequest,
    SignUpRequest,
    SocialLoginRequest,
    UserUpdateRequest,
)
from app.models.allergy import Allergy
from app.models.chronic_disease import ChronicDisease
from app.models.user import User
from app.repositories.user import UserRepository
from app.utils.common import normalize_phone_number, redis_client
from app.utils.security import create_access_token, create_refresh_token, hash_password, verify_password


class UserManageService:
    """
    사용자 계정 관리(회원가입, 로그인, 정보 수정, 탈퇴)를 담당하는 서비스 클래스입니다.
    """

    def __init__(self):
        self.user_repo = UserRepository()
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # 회원가입
    async def signup(self, data: SignUpRequest) -> User:
        """
        새로운 사용자를 등록합니다. 필수 약관 동의 및 중복 검사를 수행합니다.

        Args:
            data (SignUpRequest): 회원가입에 필요한 사용자 정보

        Returns:
            User: 생성된 사용자 DB 객체
        """
        if not data.is_terms_agreed or not data.is_privacy_agreed:
            raise HTTPException(status_code=400, detail="필수 약관에 동의해야 합니다.")

        # ID(Email) 중복 체크
        await self.check_id_exists(data.id)

        # 전화번호 정규화 및 중복 체크
        normalized_phone = normalize_phone_number(data.phone_number)
        await self.check_phone_number_exists(normalized_phone)

        # Pydantic → dict 변환
        user_data = data.model_dump()

        # 데이터 가공
        user_data["phone_number"] = normalized_phone
        user_data["password"] = hash_password(data.password)

        async with in_transaction():
            user: User = await self.user_repo.create_user(user_data)  # type: ignore[assignment]
            return user

    async def login(self, data: LoginRequest, remember_me: bool = False) -> dict:
        """
        사용자 아이디와 비밀번호를 검증하고 액세스 및 리프레시 토큰을 생성합니다.

        Args:
            data (LoginRequest): 로그인 아이디(이메일) 및 비밀번호
            remember_me (bool): 토큰 만료 시간 연장 여부

        Returns:
            dict: 액세스 토큰, 리프레시 토큰 및 사용자 ID 정보
        """
        # ID(Email)로 사용자 조회
        user = await self.user_repo.get_by_id(data.id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디 또는 비밀번호가 올바르지 않습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 비밀번호 검증
        if not verify_password(data.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디 또는 비밀번호가 올바르지 않습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate tokens
        access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)

        if remember_me:
            refresh_token_expires = timedelta(minutes=config.REFRESH_TOKEN_EXPIRE_MINUTES)
        else:
            refresh_token_expires = timedelta(minutes=config.REFRESH_TOKEN_EXPIRE_MINUTES_SHORT)

        access_token = create_access_token(data={"user_id": user.id}, expires_delta=access_token_expires)
        refresh_token = create_refresh_token(data={"user_id": user.id}, expires_delta=refresh_token_expires)

        print(refresh_token)
        # Redis에 세션 저장
        await redis_client.setex(f"session:{user.id}", int(access_token_expires.total_seconds()), access_token)

        return {"access_token": access_token, "refresh_token": refresh_token, "id": user.id, "token_type": "bearer"}

    async def check_id_exists(self, id: str | EmailStr) -> User | None:
        user: User | None = await self.user_repo.get_by_id(id)  # type: ignore[assignment]
        return user

    async def check_phone_number_exists(self, phone_number: str) -> None:
        if await self.user_repo.exists_by_phone_number(phone_number):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용중인 휴대폰 번호입니다.")

    async def update_user(self, user: User, data: UserUpdateRequest) -> User:
        update_data = data.model_dump(exclude_unset=True)

        new_allergies = update_data.pop("allergies", None)
        new_diseases = update_data.pop("chronic_diseases", None)

        if "phone_number" in update_data and update_data["phone_number"]:
            normalized_phone = normalize_phone_number(update_data["phone_number"])
            if normalized_phone != user.phone_number:
                await self.check_phone_number_exists(normalized_phone)
            update_data["phone_number"] = normalized_phone

        user.update_from_dict(update_data)
        await user.save()

        # [B] 알러지 정보 업데이트 (값이 들어왔을 때만 실행)
        if new_allergies is not None:  # 빈 리스트([])일 때도 삭제 후 갱신되도록 처리
            # 기존 데이터 삭제
            await Allergy.filter(user=user).delete()
            # 새 데이터 대량 생성
            if new_allergies:
                allergy_objs = [Allergy(allergy_name=name, user=user) for name in [new_allergies]]
                await Allergy.bulk_create(allergy_objs)

        # [C] 만성 질환 정보 업데이트
        if new_diseases is not None:
            # 기존 데이터 삭제
            await ChronicDisease.filter(user=user).delete()
            # 새 데이터 대량 생성
            if new_diseases:
                disease_objs = [ChronicDisease(disease_name=name, user=user) for name in [new_diseases]]
                await ChronicDisease.bulk_create(disease_objs)

        # [D] 최신 데이터로 리프레시 (연관 데이터 포함)
        await user.fetch_related("allergies", "chronic_diseases")

        return user

    async def delete_user(self, id: str, password: str = "") -> None:
        user = await self.user_repo.get_by_id(id=id)
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="사용자를 찾을 수 없습니다.")

        # If password is provided, verify it (for me-delete, might need verification or just session check)
        if password and not verify_password(password, user.password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="비밀번호가 일치하지 않습니다.")

        await redis_client.delete(f"session:{id}")
        await user.delete()

    async def logout(self, id: str) -> None:
        await redis_client.delete(f"session:{id}")

    async def find_email(self, name: str, phone_number: str) -> str | None:
        """
        이름과 전화번호로 이메일을 찾습니다.
        """
        normalized_phone = normalize_phone_number(phone_number)
        user: User = await self.user_repo.get_by_name_and_phone(name, normalized_phone)  # type: ignore[assignment]

        return str(user.id) if user else None

    async def verify_user_for_reset(self, email: str, name: str, phone_number: str) -> None:
        """
        비밀번호 재설정을 위한 사용자 정보 검증
        """
        normalized_phone = normalize_phone_number(phone_number)
        user: User = await self.user_repo.get_by_id(email)
        if not user or user.name != name or user.phone_number != normalized_phone:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="사용자 정보가 일치하지 않습니다.")

    async def reset_password(self, id: str, new_password: str) -> None:
        """
        비밀번호를 재설정합니다.
        """
        user: User = await self.user_repo.get_by_id(id)
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="사용자를 찾을 수 없습니다.")
        user.password = hash_password(new_password)
        await user.save()

    async def change_password(self, user: User, data: ChangePasswordRequest) -> None:
        """
        비밀번호 변경
        """

        # 비밀번호 검증
        if not verify_password(data.old_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디 또는 비밀번호가 올바르지 않습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user.password = hash_password(data.new_password)

        await user.save()

    async def social_login(self, user: User, remember_me: bool = False) -> dict:
        """
        소셜 로그인 처리 (가입된 유저 객체를 직접 받음)
        """
        # Generate tokens
        access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)

        if remember_me:
            refresh_token_expires = timedelta(minutes=config.REFRESH_TOKEN_EXPIRE_MINUTES)
        else:
            refresh_token_expires = timedelta(minutes=config.REFRESH_TOKEN_EXPIRE_MINUTES_SHORT)

        access_token = create_access_token(data={"user_id": user.id}, expires_delta=access_token_expires)
        refresh_token = create_refresh_token(data={"user_id": user.id}, expires_delta=refresh_token_expires)

        # Redis에 세션 저장 시 문자열 값 그대로 저장해야 get_request_user와 매칭됨
        await redis_client.setex(f"session:{user.id}", int(access_token_expires.total_seconds()), access_token)

        return {"access_token": access_token, "refresh_token": refresh_token, "id": user.id, "token_type": "bearer"}

    async def google_login(self, code) -> HTMLResponse:
        """
        구글 로그인 처리
        """
        async with httpx.AsyncClient() as client:
            # --- 1단계: 인가 코드를 access_token으로 교환 ---
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "code": code,
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "redirect_uri": config.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            }

            token_res = await client.post(token_url, data=token_data)
            if token_res.status_code != 200:
                raise HTTPException(status_code=400, detail="구글 토큰 발급 실패")

            google_tokens = token_res.json()
            google_access_token = google_tokens.get("access_token")

            # --- 2단계: access_token으로 구글 사용자 정보 가져오기 ---
            user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            user_res = await client.get(user_info_url, headers={"Authorization": f"Bearer {google_access_token}"})

            if user_res.status_code != 200:
                raise HTTPException(status_code=400, detail="구글 사용자 정보 취득 실패")

            user_info = user_res.json()

        # --- 3단계: 실제 데이터를 SocialLoginRequest에 매핑 ---
        # user_info 예시: {'sub': '123...', 'email': 'abc@gmail.com', 'name': '홍길동', 'picture': '...', ...}
        social_data = SocialLoginRequest(
            id=user_info.get("email"),  # 구글 이메일
            name=user_info.get("name"),  # 구글 이름
            nickname=user_info.get("name"),  # 닉네임 (보통 이름으로 초기화)
            social_id=user_info.get("sub"),  # 구글 고유 식별자 (중요)
            provider="google",
            phone_number="",  # 구글은 기본적으로 전화번호를 주지 않음 (필요시 비워둠)
            birthday="",
            gender="",
        )

        # --- 4단계: 기존 로직 수행 (유저 체크 및 리다이렉트) ---
        existing_user = await self.check_id_exists(social_data.id)

        if existing_user:
            # 이미 가입된 유저
            tokens = await self.social_login(existing_user)

            # 팝업창에서 부모창으로 넘기고 닫는 HTML
            html_content = """
            <!DOCTYPE html>
            <html><body><script>
                if (window.opener) {
                    window.opener.postMessage({status: 'login_success'}, '*');
                    window.close();
                } else {
                    window.location.href = '/dashboard';
                }
            </script></body></html>
            """
            response = HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)

            # 쿠키 설정
            response.set_cookie(
                "access_token", tokens["access_token"], httponly=False, samesite="lax", max_age=3600 * 24 * 30
            )
            response.set_cookie(
                "refresh_token",
                tokens["refresh_token"],
                httponly=True,
                samesite="lax",
                path="/",
                max_age=config.REFRESH_TOKEN_EXPIRE_MINUTES_SHORT * 60,
            )
            response.set_cookie("user_id", str(tokens["id"]), httponly=False, samesite="lax", max_age=3600 * 24 * 30)
        else:
            # 보안을 위해 정보를 쿼리 스트링에 노출하기보다 임시 쿠키를 사용하여 전달합니다.
            html_content = """
            <!DOCTYPE html>
            <html><body><script>
                if (window.opener) {
                    window.opener.postMessage({status: 'signup_required'}, '*');
                    window.close();
                } else {
                    window.location.href = '/signup';
                }
            </script></body></html>
            """
            response = HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)
            response.set_cookie(
                "social_id", social_data.id, httponly=False, samesite="lax", max_age=3600
            )  # 프론트에서 읽을 수 있게 httponly=False
            response.set_cookie("social_name", quote(social_data.name), httponly=False, samesite="lax", max_age=3600)
            response.set_cookie(
                "social_nickname", quote(social_data.nickname), httponly=False, samesite="lax", max_age=3600
            )
            response.set_cookie(
                "social_provider", quote(social_data.provider), httponly=False, samesite="lax", max_age=3600
            )
            return response

    async def naver_login(self, code: str, state: str | None = None) -> HTMLResponse:
        """
        네이버 로그인 처리
        """
        async with httpx.AsyncClient() as client:
            # --- 1단계: 인가 코드를 access_token으로 교환 ---
            token_url = "https://nid.naver.com/oauth2.0/token"
            token_data = {
                "grant_type": "authorization_code",
                "client_id": config.NAVER_CLIENT_ID,
                "client_secret": config.NAVER_CLIENT_SECRET,
                "code": code,
                "state": state or "",
            }

            token_res = await client.post(token_url, data=token_data)
            if token_res.status_code != 200:
                raise HTTPException(status_code=400, detail="네이버 토큰 발급 실패")

            naver_tokens = token_res.json()
            naver_access_token = naver_tokens.get("access_token")

            # --- 2단계: access_token으로 네이버 사용자 정보 가져오기 ---
            user_info_url = "https://openapi.naver.com/v1/nid/me"
            user_res = await client.get(user_info_url, headers={"Authorization": f"Bearer {naver_access_token}"})

            if user_res.status_code != 200:
                raise HTTPException(status_code=400, detail="네이버 사용자 정보 취득 실패")

            user_info_json = user_res.json()
            if user_info_json.get("resultcode") != "00":
                raise HTTPException(status_code=400, detail="네이버 사용자 정보가 올바르지 않습니다")

            user_info = user_info_json.get("response", {})

        # --- 3단계: 실제 데이터를 SocialLoginRequest에 매핑 ---
        # user_info 예시: {'email': 'abc@naver.com', 'name': '홍길동', 'id': 'unique_id', 'mobile': '010-1234-5678'}
        social_data = SocialLoginRequest(
            id=user_info.get("email"),  # 네이버 이메일
            name=user_info.get("name"),  # 네이버 이름
            nickname=user_info.get("nickname") or user_info.get("name"),  # 닉네임 (없으면 이름으로)
            social_id=user_info.get("id"),  # 네이버 고유 식별자
            provider="naver",
            phone_number=user_info.get("mobile"),  # 전화번호 (옵션)
            birthday=user_info.get("birthyear") + "-" + user_info.get("birthday"),
            gender="남자" if user_info.get("gender") == "M" else "여자",
        )

        # --- 4단계: 기존 로직 수행 (유저 체크 및 팝업창 닫기 응답) ---
        existing_user = await self.check_id_exists(social_data.id)

        if existing_user:
            # 이미 가입된 유저
            tokens = await self.social_login(existing_user)

            # 팝업창에서 부모창으로 넘기고 닫는 HTML
            html_content = """
            <!DOCTYPE html>
            <html><body><script>
                if (window.opener) {
                    window.opener.postMessage({status: 'login_success'}, '*');
                    window.close();
                } else {
                    window.location.href = '/dashboard';
                }
            </script></body></html>
            """
            response = HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)

            # 쿠키 설정
            response.set_cookie(
                "access_token", tokens["access_token"], httponly=False, samesite="lax", max_age=3600 * 24 * 30
            )
            response.set_cookie("user_id", str(tokens["id"]), httponly=False, samesite="lax", max_age=3600 * 24 * 30)
            return response
        else:
            # 회원가입 필요
            html_content = """
            <!DOCTYPE html>
            <html><body><script>
                if (window.opener) {
                    window.opener.postMessage({status: 'signup_required'}, '*');
                    window.close();
                } else {
                    window.location.href = '/signup';
                }
            </script></body></html>
            """
            response = HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)
            response.set_cookie("social_id", social_data.id, httponly=False, samesite="lax", max_age=3600)
            response.set_cookie("social_name", quote(social_data.name), httponly=False, samesite="lax", max_age=3600)
            response.set_cookie(
                "social_nickname", quote(social_data.nickname), httponly=False, samesite="lax", max_age=3600
            )
            response.set_cookie(
                "social_phone_number", quote(social_data.phone_number), httponly=False, samesite="lax", max_age=3600
            )
            response.set_cookie(
                "social_birthday", quote(social_data.birthday), httponly=False, samesite="lax", max_age=3600
            )
            response.set_cookie(
                "social_gender", quote(social_data.gender), httponly=False, samesite="lax", max_age=3600
            )
            response.set_cookie(
                "social_provider", quote(social_data.provider), httponly=False, samesite="lax", max_age=3600
            )
            return response
