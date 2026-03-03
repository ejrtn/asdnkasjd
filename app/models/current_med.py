from enum import Enum
from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.user import User


class DoseTime(str, Enum):
    MORNING = "아침"
    LUNCH = "점심"
    DINNER = "저녁"
    BEDTIME = "취침 전"
    UNKNOWN = "UNKNOWN"


class CurrentMed(models.Model):
    """
    사용자가 현재 실제로 복용 중인 약물 목록을 관리하는 모델입니다.
    처방전 분석 또는 직접 입력을 통해 등록되며 AI 가이드 생성의 핵심 소스입니다.
    """

    id = fields.IntField(pk=True)
    # 승인된 약물 이름 (여기 데이터가 RAG의 핵심 소스)
    medication_name = fields.CharField(max_length=255)
    one_dose = fields.CharField(max_length=255)  # 1회 용량 (예: 500mg)
    daily_dose_count = fields.CharField(max_length=255)  # 1일 복용 횟수
    one_dose_count = fields.CharField(max_length=255)  # 1회 복용 개수 (예: 1정)
    dose_time = fields.CharEnumField(DoseTime, description="복용 시간")
    added_from = fields.CharField(max_length=20)  # 출처 (OCR_PRESCRIPTION, PILL_SCAN 등)
    start_date = fields.CharField(max_length=255)  # 복용 시작 시점
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField("models.User", related_name="current_meds")

    class Meta:
        table = "current_meds"
