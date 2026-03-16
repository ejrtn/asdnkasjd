from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.pill_recognitions import PillRecognition
    from app.models.prescription_drug import PrescriptionDrug
    from app.models.user import User


class CurrentMed(models.Model):
    """
    사용자가 현재 실제로 복용 중인 약물 목록을 관리하는 모델입니다.
    처방전 분석 또는 직접 입력을 통해 등록되며 AI 가이드 생성의 핵심 소스입니다.
    """

    id = fields.IntField(pk=True)
    # 약물 이름 (필수, RAG의 핵심 소스)
    medication_name = fields.CharField(max_length=255)

    # UI 구조에 맞춘 선택 필드
    one_dose_amount = fields.CharField(max_length=255, null=True)  # 1회 투약량 (예: 500mg, 1정)
    one_dose_count = fields.CharField(max_length=255, null=True)  # 1회 투여횟수
    total_days = fields.CharField(max_length=255, null=True)  # 총 투약일수
    instructions = fields.TextField(null=True)  # 용법 (예: 식후 30분)

    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField("models.User", related_name="current_meds")

    # 약물 식별(PillRecognition)과의 1:1 관계
    pill_recognition: fields.OneToOneRelation["PillRecognition"] | None = fields.OneToOneField(
        "models.PillRecognition", related_name="current_med", null=True
    )

    # 처방전 약물(PrescriptionDrug)과의 1:N 관계 (역방향)
    prescription_drugs: fields.ReverseRelation["PrescriptionDrug"]

    class Meta:
        table = "current_meds"
