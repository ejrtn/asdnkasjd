from enum import Enum
from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.user import User


class GlucoseMeasureType(str, Enum):
    FASTING = "FASTING"  # 공복
    BEFORE_MEAL = "BEFORE_MEAL"  # 식전
    AFTER_MEAL = "AFTER_MEAL"  # 식후
    BEDTIME = "BEDTIME"  # 취침 전
    RANDOM = "RANDOM"  # 임의


class BloodSugarRecord(models.Model):
    """
    혈당 기록(동적 기록 수첩)
    - 1 user : N records
    """

    id = fields.IntField(pk=True)

    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User",
        related_name="blood_sugar_records",
        on_delete=fields.CASCADE,
        description="사용자",
    )

    glucose_mg_dl = fields.FloatField(description="혈당(mg/dL)")
    measure_type = fields.CharEnumField(
        GlucoseMeasureType,
        default=GlucoseMeasureType.RANDOM,
        description="측정 상황(공복/식전/식후/취침전/임의)",
    )

    recorded_at = fields.DatetimeField(description="실제 측정 시각(사용자 입력/측정 시각)")
    created_at = fields.DatetimeField(auto_now_add=True, description="서버 저장 시각")

    class Meta:
        table = "blood_sugar_records"
        table_description = "혈당 기록(mg/dL + 측정상황)"

    def __str__(self) -> str:
        return f"BG(user={getattr(self, 'user_id', 'N/A')}, {self.glucose_mg_dl}, {self.measure_type})"
