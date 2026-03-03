from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.security import get_request_user
from app.dtos.alarm import AlarmCreateRequest, AlarmResponse, AlarmToggleRequest, AlarmUpdateRequest
from app.models.user import User
from app.services.alarm import AlarmService

alarm_router = APIRouter(prefix="/alarms", tags=["alarm"])


@alarm_router.get("", response_model=list[AlarmResponse])
async def get_alarms(
    user: Annotated[User, Depends(get_request_user)],
    alarm_type: str | None = None,
) -> list[AlarmResponse]:
    service = AlarmService()
    return await service.get_user_alarms(user, alarm_type)


@alarm_router.post("", status_code=status.HTTP_201_CREATED, response_model=AlarmResponse)
async def create_alarm(request: AlarmCreateRequest, user: Annotated[User, Depends(get_request_user)]) -> AlarmResponse:
    """
    [ALARM] 복약 알람 생성
    """
    service = AlarmService()
    try:
        return await service.create_alarm(user, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@alarm_router.patch("/{alarm_id}", response_model=AlarmResponse)
async def update_alarm(
    alarm_id: int, request: AlarmUpdateRequest, user: Annotated[User, Depends(get_request_user)]
) -> AlarmResponse:
    """
    [ALARM] 복약 알람 수정
    """
    service = AlarmService()
    try:
        return await service.update_alarm(user, alarm_id, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@alarm_router.patch("/{alarm_id}/toggle", response_model=AlarmResponse)
async def toggle_alarm(
    alarm_id: int, request: AlarmToggleRequest, user: Annotated[User, Depends(get_request_user)]
) -> AlarmResponse:
    """
    [ALARM] 복약 알람 온/오프 토글
    """
    service = AlarmService()
    try:
        return await service.toggle_alarm(user, alarm_id, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@alarm_router.delete("/{alarm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alarm(alarm_id: int, user: Annotated[User, Depends(get_request_user)]) -> None:
    """
    [ALARM] 복약 알람 삭제
    """
    service = AlarmService()
    try:
        await service.delete_alarm(user, alarm_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@alarm_router.post("/history/confirm/{alarm_id}", status_code=status.HTTP_200_OK)
async def confirm_alarm(alarm_id: int, user: Annotated[User, Depends(get_request_user)]) -> dict:
    """
    [ALARM] 알람 확인 (복약/측정 완료 체크)
    """
    from app.models.alarm_history import AlarmHistory

    history = await AlarmHistory.filter(alarm_id=alarm_id).order_by("-sent_at").first()
    if history:
        history.is_confirmed = True
        await history.save()
    return {"detail": "확인 완료"}


@alarm_router.get("/{alarm_id}/history")
async def get_alarm_history(alarm_id: int, user: Annotated[User, Depends(get_request_user)]) -> dict:
    """
    [ALARM] 복약 알람 발송/확인 이력 조회
    """
    return {"items": []}


@alarm_router.patch("/history/{history_id}")
async def confirm_alarm_history(history_id: int, user: Annotated[User, Depends(get_request_user)]) -> dict:
    """
    [ALARM] 복약 완료 체크
    """
    return {"detail": "복약 확인 되었습니다."}


@alarm_router.post("/history/{history_id}/confirm-link")
async def confirm_alarm_link(history_id: int, confirm_token: str) -> dict:
    """
    [ALARM] 카카오 버튼/링크 기반 복약완료 체크.
    """
    return {"detail": "복약 확인 완료"}
