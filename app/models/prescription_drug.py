from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.current_med import CurrentMed
    from app.models.prescription import Prescription


class PrescriptionDrug(models.Model):
    """
    처방전에 포함된 개별 약품 상세 정보를 관리하는 모델입니다.
    용량, 복용 빈도 및 기간 정보를 포함하며 특정 처방전(Prescription)에 속합니다.
    """

    id = fields.IntField(pk=True)
    standard_drug_name = fields.CharField(max_length=255)  # AI가 식별한 표준 약물명
    dosage_amount = fields.FloatField(null=True)  # 1회 투여량
    daily_frequency = fields.IntField(null=True)  # 하루 횟수
    duration_days = fields.IntField(null=True)  # 복용 일수
    # [핵심] 사용자가 복용 명단 추가 승인 시 True로 변경
    is_linked_to_meds = fields.BooleanField(default=False)
    prescription: fields.ForeignKeyRelation["Prescription"] = fields.ForeignKeyField(
        "models.Prescription", related_name="drugs"
    )

    # CurrentMed와의 N:1 관계 (처방전 약품이 실제 복용 목록과 연동될 때 사용)
    current_med: fields.ForeignKeyRelation["CurrentMed"] | None = fields.ForeignKeyField(
        "models.CurrentMed", related_name="prescription_drugs", null=True
    )

    class Meta:
        table = "prescription_drugs"
