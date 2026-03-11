from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.security import get_request_user
from app.dtos.health import DashboardHealthMetricSummaryResponse
from app.models.user import User
from app.repositories.health_profile import HealthProfileRepository
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _format_sleep_hours(sleep_hours: float | None) -> str:
    """수면 시간을 포맷팅합니다."""
    if sleep_hours is None:
        return "-"
    hours = int(sleep_hours)
    minutes = int(round((sleep_hours - hours) * 60))
    return f"{hours}시간 {minutes}분" if minutes else f"{hours}시간"


def _get_sleep_change_text(sleep_change: str | None) -> str:
    """수면 변화를 텍스트로 변환합니다."""
    if not sleep_change:
        return "➖ 정보 없음"
    if sleep_change == "감소":
        return "⬇ 감소"
    if sleep_change == "증가":
        return "⬆ 증가"
    if sleep_change == "변화없음":
        return "➖ 변화 없음"
    return "➖ 모름"


def _get_weight_change_text(weight_change: str | None) -> str:
    """체중 변화를 텍스트로 변환합니다."""
    if not weight_change:
        return "➖ 정보 없음"
    if weight_change == "감소":
        return "⬇ 감소"
    if weight_change == "증가":
        return "⬆ 증가"
    if weight_change == "변화없음":
        return "➖ 변화 없음"
    return "➖ 모름"


@router.get("/summary")
async def get_dashboard_summary(user: Annotated[User, Depends(get_request_user)]):
    """대시보드 요약 데이터를 반환합니다."""
    health_profile_repo = HealthProfileRepository()
    profile = await health_profile_repo.get_by_user_id(user.id)

    sleep_value = "-"
    sleep_label = "평균 수면 시간"
    sleep_change = "➖ 정보 없음"

    weight_value = "-"
    weight_label = "현재 체중"
    weight_change = "➖ 정보 없음"

    if profile:
        sleep_value = _format_sleep_hours(profile.sleep_hours)
        sleep_change = _get_sleep_change_text(profile.sleep_change)
        weight_value = f"{profile.weight_kg}kg" if profile.weight_kg else "-"
        weight_change = _get_weight_change_text(profile.weight_change)

    return {
        "health_score": 82,
        "health_status": "안정 상태",
        "blood_pressure": {
            "value": "132 / 84",
            "unit": "mmHg",
            "label": "최근 7일 평균",
            "status": "지난주 대비 큰 변동 없음",
        },
        "blood_sugar": {"value": "108", "unit": "mg/dL", "label": "최근 7일 평균 공복", "status": "최근 3일 소폭 상승"},
        "sleep": {"value": sleep_value, "label": sleep_label, "change": sleep_change},
        "weight": {"value": weight_value, "label": weight_label, "change": weight_change},
        "medications": [
            {"time": "08:00", "name": "아침약", "status": "completed"},
            {"time": "20:00", "name": "저녁약", "status": "pending"},
        ],
        "next_alarm_minutes": 192,
        "analysis": {"title": "처방전 분석 완료", "result": "약물 상호작용 없음", "status": "safe"},
    }


@router.get("/health-metric-summary", response_model=DashboardHealthMetricSummaryResponse)
async def get_health_metric_summary(
    user: Annotated[User, Depends(get_request_user)],
):
    """오늘 혈압/혈당 기록 요약"""
    service = DashboardService()
    return await service.generate_health_metric_summary(user)


@router.get("/insights")
async def get_insights(user: Annotated[User, Depends(get_request_user)]):
    """사용자 건강 정보 기반 AI 인사이트 생성"""
    service = DashboardService()
    return await service.generate_insights(user)
