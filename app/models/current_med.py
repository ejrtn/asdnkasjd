from enum import StrEnum
from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.pill_recognitions import PillRecognition
    from app.models.prescription_drug import PrescriptionDrug
    from app.models.user import User


class DoseTime(StrEnum):
    MORNING = "아침"
    LUNCH = "점심"
    DINNER = "저녁"
    BEDTIME = "취침 전"


class AddedFrom(StrEnum):
    UNKNOWN = "모름"
    HOSPITAL = "병원 처방"
    PHARMACY = "약국 구매"


class CurrentMed(models.Model):
    """
    사용자가 현재 실제로 복용 중인 약물 목록을 관리하는 모델입니다.
    처방전 분석 또는 직접 입력을 통해 등록되며 AI 가이드 생성의 핵심 소스입니다.
    """

    id = fields.IntField(pk=True)
    # 승인된 약물 이름 (여기 데이터가 RAG의 핵심 소스)
    medication_name = fields.CharField(max_length=255)
    one_dose = fields.CharField(max_length=255, null=True)  # 1회 용량 (예: 500mg)
    daily_dose_count = fields.CharField(max_length=255, null=True)  # 1일 복용 횟수
    one_dose_count = fields.CharField(max_length=255, null=True)  # 1회 복용 개수 (예: 1정)
    dose_time = fields.CharEnumField(DoseTime, description="복용 시간")
    added_from = fields.CharEnumField(AddedFrom, description="출처")  # 출처 (약국, 처방전)
    start_date = fields.CharField(max_length=255, null=True)  # 복용 시작 시점
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField("models.User", related_name="current_meds")

    # 약물 식별(PillRecognition)과의 1:1 관계
    pill_recognition: fields.OneToOneRelation["PillRecognition"] | None = fields.OneToOneField(
        "models.PillRecognition", related_name="current_med", null=True
    )

    # 처방전 약물(PrescriptionDrug)과의 1:N 관계 (역방향)
    prescription_drugs: fields.ReverseRelation["PrescriptionDrug"]

    class Meta:
        table = "current_meds"
