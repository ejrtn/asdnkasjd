from fastapi import APIRouter

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_dashboard_summary(user_id: str | None = None):
    """대시보드 요약 데이터를 반환합니다."""
    
    return {
        "health_score": 82,
        "health_status": "안정 상태",
        "blood_pressure": {
            "value": "132 / 84",
            "unit": "mmHg",
            "label": "최근 7일 평균",
            "status": "지난주 대비 큰 변동 없음"
        },
        "blood_sugar": {
            "value": "108",
            "unit": "mg/dL",
            "label": "최근 7일 평균 공복",
            "status": "최근 3일 소폭 상승"
        },
        "sleep": {
            "value": "6시간 12분",
            "label": "평균 수면 시간",
            "change": "⬇ 감소 (−40분)"
        },
        "weight": {
            "value": "68.2kg",
            "label": "현재 체중",
            "change": "➖ 변화 없음"
        },
        "medications": [
            {
                "time": "08:00",
                "name": "아침약",
                "status": "completed"
            },
            {
                "time": "20:00",
                "name": "저녁약",
                "status": "pending"
            }
        ],
        "next_alarm_minutes": 192,
        "analysis": {
            "title": "처방전 분석 완료",
            "result": "약물 상호작용 없음",
            "status": "safe"
        }
    }
