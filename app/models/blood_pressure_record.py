from enum import StrEnum
from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.user import User


class RecordTime(StrEnum):
    MORNING = "아침"
    DINNER = "저녁"
    RANDOM = "임의"


class BloodPressureRecord(models.Model):
    """
    혈압 기록(동적 기록 수첩)
    - 1 user : N records
    """

    id = fields.IntField(pk=True)

    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User",
        related_name="blood_pressure_records",
        on_delete=fields.CASCADE,
        description="사용자",
    )

    systolic = fields.IntField(description="수축기(mmHg)")
    diastolic = fields.IntField(description="이완기(mmHg)")

    measure_type = fields.CharEnumField(
        RecordTime,
        description="측정 상황",
    )
    created_at = fields.DatetimeField(auto_now_add=True, description="서버 저장 시각")

    class Meta:
        table = "blood_pressure_records"
        table_description = "혈압 기록(수축기/이완기/맥박)"

    def __str__(self) -> str:
        return f"BP(user={getattr(self, 'user_id', 'N/A')}, {self.systolic}/{self.diastolic})"
