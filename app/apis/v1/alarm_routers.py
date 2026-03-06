from datetime import datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.logger import default_logger
from app.dependencies.security import get_request_user
from app.dtos.alarm import (
    AlarmCreateRequest,
    AlarmHistoryResponse,
    AlarmResponse,
    AlarmToggleRequest,
    AlarmUpdateRequest,
    DashboardAlarmSummaryResponse,
)
from app.models.alarm_history import AlarmHistory
from app.models.user import User
from app.services.alarm import AlarmService

alarm_router = APIRouter(prefix="/alarms", tags=["alarm"])


@alarm_router.get("", response_model=list[AlarmResponse])
async def get_alarms(
    user: Annotated[User, Depends(get_request_user)],
    alarm_type: str | None = None,
) -> list[AlarmResponse]:
    default_logger.info("[Alarm] get_alarms - 로그인")
    service = AlarmService()
    return await service.get_user_alarms(user, alarm_type)


@alarm_router.post("", status_code=status.HTTP_201_CREATED, response_model=AlarmResponse)
async def create_alarm(request: AlarmCreateRequest, user: Annotated[User, Depends(get_request_user)]) -> AlarmResponse:
    """
    [ALARM] 복약 알람 생성
    """
    default_logger.info("[Alarm] create_alarm - 로그인")
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
    default_logger.info("[Alarm] update_alarm - 로그인")
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
    default_logger.info("[Alarm] toggle_alarm - 로그인")
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
    default_logger.info("[Alarm] delete_alarm - 로그인")
    service = AlarmService()
    try:
        await service.delete_alarm(user, alarm_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@alarm_router.get("/due")
async def get_due_alarms(user: Annotated[User, Depends(get_request_user)]) -> list[dict]:
    """
    [ALARM] 현재 웹 화면에서 띄워야 할 알람 조회
    - 최근 2분 내 발송된 알람
    - 아직 확인하지 않은 알람
    - 현재 로그인 사용자 기준
    """
    default_logger.info("[Alarm] get_due_alarms - 로그인")

    now = datetime.now(ZoneInfo("Asia/Seoul"))
    since = now - timedelta(minutes=2)

    histories = (
        await AlarmHistory.filter(
            is_confirmed=False,
            sent_at__gte=since,
            alarm__user=user,
        )
        .prefetch_related("alarm__current_med")
        .order_by("-sent_at")
    )

    items = []

    for history in histories:
        alarm = history.alarm
        if not alarm:
            continue

        med_name = alarm.current_med.medication_name if alarm.current_med else None

        if alarm.alarm_type == "MED":
            title = "복약 알람"
            body = f"{med_name or '약'} 복용 시간입니다."
        elif alarm.alarm_type == "BP_MORNING":
            title = "혈압 알람"
            body = "아침 혈압 측정 시간입니다."
        elif alarm.alarm_type == "BP_EVENING":
            title = "혈압 알람"
            body = "저녁 혈압 측정 시간입니다."
        elif alarm.alarm_type == "BS_FASTING":
            title = "혈당 알람"
            body = "아침 공복 혈당 측정 시간입니다."
        elif alarm.alarm_type == "BS_POSTMEAL":
            title = "혈당 알람"
            body = "식후 2시간 혈당 측정 시간입니다."
        elif alarm.alarm_type == "BS_BEDTIME":
            title = "혈당 알람"
            body = "취침 전 혈당 측정 시간입니다."
        else:
            title = "알람"
            body = "알람 시간이 되었습니다."

        items.append(
            {
                "history_id": history.id,
                "alarm_id": alarm.id,
                "alarm_type": alarm.alarm_type,
                "title": title,
                "body": body,
                "sent_at": history.sent_at.isoformat() if history.sent_at else None,
            }
        )

    return items


@alarm_router.post("/history/confirm/{alarm_id}", status_code=status.HTTP_200_OK)
async def confirm_alarm(alarm_id: int, user: Annotated[User, Depends(get_request_user)]) -> dict:
    """
    [ALARM] 알람 확인 (복약/측정 완료 체크)
    """
    default_logger.info("[Alarm] confirm_alarm - 로그인")
    from app.models.alarm_history import AlarmHistory

    history = (
        await AlarmHistory.filter(
            alarm_id=alarm_id,
            alarm__user=user,
        )
        .order_by("-sent_at")
        .first()
    )
    if history:
        history.is_confirmed = True
        await history.save()
    return {"detail": "확인 완료"}


@alarm_router.get("/dashboard-summary", response_model=DashboardAlarmSummaryResponse)
async def get_dashboard_alarm_summary(
    user: Annotated[User, Depends(get_request_user)],
) -> DashboardAlarmSummaryResponse:
    """
    [ALARM] 대시보드용 오늘의 복약 & 알림 요약
    - 현재 시각 기준 직전 알람 1개
    - 현재 시각 기준 직후 알람 1개
    - 다음 알림까지 남은 시간
    """
    default_logger.info("[Alarm] get_dashboard_alarm_summary - 로그인")
    service = AlarmService()
    return await service.get_dashboard_alarm_summary(user)


@alarm_router.get("/history", response_model=list[AlarmHistoryResponse])
async def get_alarm_histories(
    user: Annotated[User, Depends(get_request_user)],
    limit: int = 30,
) -> list[AlarmHistoryResponse]:
    """
    [ALARM] 로그인 사용자의 알람 기록 조회
    """
    default_logger.info("[Alarm] get_alarm_histories - 로그인")
    service = AlarmService()
    return await service.get_user_alarm_histories(user, limit)


@alarm_router.get("/{alarm_id}/history")
async def get_alarm_history(alarm_id: int, user: Annotated[User, Depends(get_request_user)]) -> dict:
    """
    [ALARM] 복약 알람 발송/확인 이력 조회
    """
    default_logger.info("[Alarm] get_alarm_history - 로그인")
    return {"items": []}


@alarm_router.patch("/history/{history_id}")
async def confirm_alarm_history(history_id: int, user: Annotated[User, Depends(get_request_user)]) -> dict:
    """
    [ALARM] alarm_history 단건 확인 처리
    """
    default_logger.info("[Alarm] confirm_alarm_history - 로그인")
    service = AlarmService()

    try:
        await service.confirm_alarm_history(user, history_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    return {"detail": "알람 확인 되었습니다."}


@alarm_router.post("/history/{history_id}/confirm-link")
async def confirm_alarm_link(history_id: int, confirm_token: str) -> dict:
    """
    [ALARM] 카카오 버튼/링크 기반 복약완료 체크.
    """
    default_logger.info("[Alarm] confirm_alarm_link - 로그아웃")
    return {"detail": "복약 확인 완료"}
