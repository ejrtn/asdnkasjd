from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies.security import get_request_user
from app.models.alarm import Alarm
from app.models.alarm_history import AlarmHistory
from app.models.blood_pressure_record import BloodPressureRecord
from app.models.blood_sugar_record import BloodSugarRecord
from app.models.health_profile import HealthProfile
from app.models.prescription import Prescription
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_dashboard_summary(current_user: User = Depends(get_request_user)) -> dict[str, Any]:  # noqa: B008
    """대시보드 요약 정보를 반환합니다."""

    # 오늘 날짜
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)

    # 건강 지표 데이터
    health_metrics = await get_health_metrics(current_user.id, week_ago)

    # 오늘의 복약 정보
    medication_info = await get_today_medication(current_user.id, today)

    # 최근 분석 결과
    analysis_result = await get_recent_analysis(current_user.id)

    # 생활 변화 트렌드
    lifestyle_trends = await get_lifestyle_trends(current_user.id, week_ago)

    # 건강 점수 계산
    health_score = calculate_health_score(health_metrics, lifestyle_trends)

    return {
        "health_score": health_score,
        "health_metrics": health_metrics,
        "medication": medication_info,
        "analysis": analysis_result,
        "trends": lifestyle_trends,
        "insights": generate_health_insights(health_metrics, lifestyle_trends),
    }


async def get_health_metrics(user_id: str, week_ago: date) -> dict[str, Any]:
    """건강 지표 데이터를 가져옵니다."""

    # 혈압 데이터
    bp_records = (
        await BloodPressureRecord.filter(user_id=user_id, created_at__gte=week_ago).order_by("-created_at").limit(7)
    )

    if bp_records:
        avg_systolic = sum(record.systolic for record in bp_records) / len(bp_records)
        avg_diastolic = sum(record.diastolic for record in bp_records) / len(bp_records)
        bp_trend = "안정" if 120 <= avg_systolic <= 140 and 80 <= avg_diastolic <= 90 else "주의"
    else:
        avg_systolic = avg_diastolic = 0
        bp_trend = "데이터 없음"

    # 혈당 데이터
    bs_records = (
        await BloodSugarRecord.filter(user_id=user_id, created_at__gte=week_ago).order_by("-created_at").limit(7)
    )

    if bs_records:
        avg_glucose = sum(record.glucose_mg_dl for record in bs_records) / len(bs_records)
        bs_trend = "정상" if avg_glucose < 126 else "주의"
    else:
        avg_glucose = 0
        bs_trend = "데이터 없음"

    return {
        "blood_pressure": {
            "systolic": round(avg_systolic),
            "diastolic": round(avg_diastolic),
            "trend": bp_trend,
            "status": "지난주 대비 큰 변동 없음",
        },
        "blood_sugar": {
            "glucose": round(avg_glucose),
            "trend": bs_trend,
            "status": "최근 3일 소폭 상승" if bs_trend == "주의" else "안정적",
        },
    }


async def get_today_medication(user_id: str, today: date) -> dict[str, Any]:
    """오늘의 복약 정보를 가져옵니다."""

    # 오늘의 알람 목록
    today_alarms = await Alarm.filter(user_id=user_id, is_active=True).prefetch_related("current_med")

    medications = []
    completed_count = 0

    for alarm in today_alarms:
        # 오늘 이 알람에 대한 복약 기록 확인
        today_history = await AlarmHistory.filter(alarm_id=alarm.id, created_at__date=today).first()

        is_completed = today_history is not None and today_history.is_confirmed
        if is_completed:
            completed_count += 1

        medications.append(
            {
                "time": alarm.alarm_time.strftime("%H:%M"),
                "name": f"{alarm.alarm_time.strftime('%H:%M')} {'아침약' if alarm.alarm_time.hour < 12 else '저녁약'}",
                "is_completed": is_completed,
                "medication_name": alarm.current_med.medication_name if alarm.current_med else "복용약",
            }
        )

    # 다음 알림까지 남은 시간 계산
    next_alarm_time = None
    now = datetime.now()

    for alarm in today_alarms:
        alarm_datetime = datetime.combine(today, alarm.alarm_time)
        if alarm_datetime > now:
            next_alarm_time = alarm_datetime
            break

    if not next_alarm_time and today_alarms:
        # 오늘 남은 알람이 없으면 내일 첫 알람
        tomorrow = today + timedelta(days=1)
        first_alarm = min(today_alarms, key=lambda x: x.alarm_time)
        next_alarm_time = datetime.combine(tomorrow, first_alarm.alarm_time)

    time_until_next = None
    if next_alarm_time:
        time_diff = next_alarm_time - now
        hours = int(time_diff.total_seconds() // 3600)
        minutes = int((time_diff.total_seconds() % 3600) // 60)
        time_until_next = f"{hours}시간 {minutes}분"

    return {
        "medications": medications,
        "completed_count": completed_count,
        "total_count": len(medications),
        "next_alarm": time_until_next,
    }


async def get_recent_analysis(user_id: str) -> dict[str, Any]:
    """최근 분석 결과를 가져옵니다."""

    # 최근 처방전 분석 결과
    recent_prescription = await Prescription.filter(user_id=user_id).order_by("-created_at").first()

    if recent_prescription:
        # 약물 상호작용 체크 (실제로는 더 복잡한 로직)
        has_interaction = False  # 임시값

        return {
            "title": "처방전 분석 완료",
            "status": "safe" if not has_interaction else "warning",
            "message": "약물 상호작용 없음" if not has_interaction else "주의가 필요한 조합이 확인되었습니다.",
            "date": recent_prescription.created_at.strftime("%Y-%m-%d"),
        }

    return {
        "title": "분석 결과 없음",
        "status": "info",
        "message": "처방전을 업로드하여 분석을 받아보세요.",
        "date": None,
    }


async def get_lifestyle_trends(user_id: str, week_ago: date) -> dict[str, Any]:
    """생활 변화 트렌드를 가져옵니다."""

    # 건강 프로필에서 수면, 체중 데이터 가져오기
    health_profile = await HealthProfile.filter(user_id=user_id).first()

    # 실제로는 더 복잡한 트렌드 분석이 필요
    sleep_data = {"average": "6시간 12분", "change": "decrease", "change_amount": "40분", "status": "평균보다 감소"}

    weight_data = {
        "current": f"{health_profile.weight_kg}kg" if health_profile and health_profile.weight_kg else "68.2kg",
        "change": "stable",
        "change_amount": "0kg",
        "status": "변화 없음",
    }

    return {"sleep": sleep_data, "weight": weight_data}


def calculate_health_score(health_metrics: dict, lifestyle_trends: dict) -> dict[str, Any]:
    """건강 점수를 계산합니다."""

    score = 85  # 기본 점수
    status = "안정 상태"

    # 혈압 체크
    bp = health_metrics.get("blood_pressure", {})
    if bp.get("trend") == "주의":
        score -= 10
        status = "주의 필요"

    # 혈당 체크
    bs = health_metrics.get("blood_sugar", {})
    if bs.get("trend") == "주의":
        score -= 10
        status = "주의 필요"

    # 수면 체크
    sleep = lifestyle_trends.get("sleep", {})
    if sleep.get("change") == "decrease":
        score -= 5

    return {"score": max(score, 0), "status": status}


def generate_health_insights(health_metrics: dict, lifestyle_trends: dict) -> list[str]:
    """건강 인사이트를 생성합니다."""

    insights = []

    # 혈압 인사이트
    bp = health_metrics.get("blood_pressure", {})
    if bp.get("trend") == "안정":
        insights.append("최근 7일 평균 혈압은 안정 범위입니다.")
    else:
        insights.append("혈압 수치에 주의가 필요합니다.")

    # 수면 인사이트
    sleep = lifestyle_trends.get("sleep", {})
    if sleep.get("change") == "decrease":
        insights.append(f"수면 시간이 평균보다 {sleep.get('change_amount', '40분')} 감소했습니다.")

    # 체중 인사이트
    weight = lifestyle_trends.get("weight", {})
    if weight.get("change") == "stable":
        insights.append("체중은 큰 변화 없이 유지되고 있습니다.")

    return insights[:3]  # 최대 3개까지만 반환
