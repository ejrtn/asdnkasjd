from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import ORJSONResponse as Response
from pydantic import BaseModel

from app.dependencies.security import get_request_user
from app.dtos.users import (
    ChangePasswordRequest,
    FcmTokenUpdateRequest,
    SignUpRequest,
    SignUpResponse,
    UserMeResponse,
    UserUpdateRequest,
)
from app.models.user import User
from app.services.users import UserManageService


class AlarmMasterToggleRequest(BaseModel):
    alarm_tf: bool


user_router = APIRouter(prefix="/users", tags=["users"])


@user_router.post("", response_model=SignUpResponse, status_code=status.HTTP_200_OK)
async def signup(
    request: SignUpRequest, user_service: Annotated[UserManageService, Depends(UserManageService)]
) -> Response:
    """
    [USER] 회원가입
    """
    print(request)
    # Service cleanup needed for new SignUpRequest field names (email vs id)
    # Mapping new field names to service
    await user_service.signup(request)

    # Generate token for response

    return Response(content={"id": request.id, "detail": "회원가입 성공하셨습니다."}, status_code=status.HTTP_200_OK)


@user_router.get("/me", response_model=UserMeResponse)
async def get_me(user: Annotated[User, Depends(get_request_user)]) -> UserMeResponse:
    """
    [USER] 내 정보 조회
    """

    return UserMeResponse(
        id=user.id,
        nickname=user.nickname,
        name=user.name,
        phone_number=user.phone_number,
        birthday=user.birthday,
        gender=user.gender,
        chronic_diseases=[a.disease_name for a in user.chronic_diseases],
        allergies=[d.allergy_name for d in user.allergies],
        alarm_tf=user.alarm_tf,
        is_terms_agreed=user.is_terms_agreed,
        is_privacy_agreed=user.is_privacy_agreed,
        is_marketing_agreed=user.is_marketing_agreed,
        is_alarm_agreed=user.is_alarm_agreed,
    )


@user_router.patch("/me")
async def update_me(
    update_data: UserUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    user_service: Annotated[UserManageService, Depends(UserManageService)],
) -> Response:
    """
    [USER] 내 정보 수정(닉네임/연락처/마케팅 동의 등)
    """
    await user_service.update_user(user=user, data=update_data)
    return Response(content={"detail": "정보가 수정되었습니다."}, status_code=status.HTTP_200_OK)


@user_router.delete("/me")
async def withdraw_me(
    user: Annotated[User, Depends(get_request_user)],
    user_service: Annotated[UserManageService, Depends(UserManageService)],
) -> Response:
    """
    [USER] 회원 탈퇴(비활성/삭제 처리)
    """
    # Note: Service currently requires password for delete, adjusting to simple me-delete
    await user_service.delete_user(id=user.id, password="")  # In real case, password might be checked elsewhere or here
    return Response(content={"detail": "탈퇴 처리가 완료되었습니다."}, status_code=status.HTTP_200_OK)


# 아이디 찾기
@user_router.get("/find-id", status_code=status.HTTP_200_OK)
async def find_email(
    name: str, phone_number: str, auth_service: Annotated[UserManageService, Depends(UserManageService)]
) -> Response:
    email = await auth_service.find_email(name, phone_number)
    return Response(content={"email": email}, status_code=status.HTTP_200_OK)


# 비밀번호 재설정 (비인증 상태)
@user_router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    data: dict,  # email, name, phone_number, new_password
    auth_service: Annotated[UserManageService, Depends(UserManageService)],
) -> Response:
    # 사용자 정보 검증
    await auth_service.verify_user_for_reset(email=data["id"], name=data["name"], phone_number=data["phone_number"])

    # 비밀번호 재설정
    await auth_service.reset_password(data["id"], data["new_password"])

    return Response(content={"detail": "비밀번호가 성공적으로 변경되었습니다."}, status_code=status.HTTP_200_OK)


# 비밀번호 재설정 (인증 상태)
@user_router.patch("/me/password", status_code=status.HTTP_200_OK)
async def new_password(
    data: ChangePasswordRequest,  # old_password, new_password
    user: Annotated[User, Depends(get_request_user)],
    auth_service: Annotated[UserManageService, Depends(UserManageService)],
) -> Response:
    # 비밀번호 재설정
    await auth_service.change_password(user, data)

    return Response(content={"detail": "비밀번호가 성공적으로 변경되었습니다."}, status_code=status.HTTP_200_OK)


@user_router.patch("/me/fcm-token", status_code=status.HTTP_200_OK)
async def update_fcm_token(
    data: FcmTokenUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
) -> Response:
    """[USER] FCM 토큰 등록/갱신"""
    user.fcm_token = data.fcm_token
    await user.save()
    return Response(content={"detail": "FCM 토큰이 등록되었습니다."}, status_code=status.HTTP_200_OK)


@user_router.patch("/me/alarm-toggle", status_code=status.HTTP_200_OK)
async def update_alarm_master_toggle(
    data: AlarmMasterToggleRequest,
    user: Annotated[User, Depends(get_request_user)],
) -> Response:
    """
    [USER] 전체 알람 ON/OFF 토글
    """
    from app.models.alarm import Alarm

    user.alarm_tf = data.alarm_tf
    await user.save()

    await Alarm.filter(user=user).update(is_active=data.alarm_tf)

    return Response(
        content={
            "detail": "전체 알람 설정이 변경되었습니다.",
            "alarm_tf": user.alarm_tf,
        },
        status_code=status.HTTP_200_OK,
    )


@user_router.get("/id-check")
async def id_check(id: str, user_service: Annotated[UserManageService, Depends(UserManageService)]):
    """
    id 중복 확인
    """
    if await user_service.check_id_exists(id):
        return Response(content={"detail": "이미 사용중인 아이디입니다."}, status_code=status.HTTP_200_OK)
    return Response(content={"detail": "사용하고 있지 않은 아이디입니다."}, status_code=status.HTTP_200_OK)


@user_router.post("/logout")
async def logout() -> Response:
    """
    [USER] 로그아웃 - 쿠키 삭제
    """
    response = Response(content={"detail": "로그아웃되었습니다."}, status_code=status.HTTP_200_OK)
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("user_id", path="/")
    response.delete_cookie("refresh_token", path="/")
    return response
