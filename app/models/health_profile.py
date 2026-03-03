from enum import Enum
from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.user import User


class SmokingStatus(str, Enum):
    NEVER = "NEVER"
    CURRENT = "CURRENT"
    FORMER = "FORMER"
    UNKNOWN = "UNKNOWN"


class DrinkingStatus(str, Enum):
    NEVER = "NEVER"
    CURRENT = "CURRENT"
    FORMER = "FORMER"
    UNKNOWN = "UNKNOWN"


class WeightChange(str, Enum):
    NONE = "NONE"  # 변화 없음
    YES = "YES"  # 변화 있음
    UNKNOWN = "UNKNOWN"  # 잘 모름


class ExerciseFrequency(str, Enum):
    NONE = "NONE"
    WEEK_1_2 = "WEEK_1_2"
    WEEK_3_4 = "WEEK_3_4"
    WEEK_5_PLUS = "WEEK_5_PLUS"
    UNKNOWN = "UNKNOWN"


class DietType(str, Enum):
    BALANCED = "BALANCED"
    LOW_SALT = "LOW_SALT"
    LOW_CARB = "LOW_CARB"
    HIGH_PROTEIN = "HIGH_PROTEIN"
    VEGETARIAN = "VEGETARIAN"
    IRREGULAR = "IRREGULAR"
    FAST_FOOD = "FAST_FOOD"
    UNKNOWN = "UNKNOWN"


class HealthProfile(models.Model):
    """
    사용자 건강 프로필(정적/준정적 정보)
    - 1 user : 1 health_profile
    """

    id = fields.IntField(pk=True)

    user: fields.OneToOneRelation["User"] = fields.OneToOneField(
        "models.User",
        related_name="health_profile",
        on_delete=fields.CASCADE,
        description="사용자",
    )

    # 가족력: 예/아니오 + 부/모 텍스트
    family_history = fields.BooleanField(default=False, description="가족력 유무(예/아니오)")
    family_history_father_note = fields.TextField(null=True, description="부 가족력(사용자 입력 텍스트)")
    family_history_mother_note = fields.TextField(null=True, description="모 가족력(사용자 입력 텍스트)")

    # 신체계측(팀 합의: 체중은 프로필에 포함)
    height_cm = fields.FloatField(null=True, description="신장(cm)")
    weight_kg = fields.FloatField(null=True, description="체중(kg)")
    weight_change = fields.CharEnumField(WeightChange, default=WeightChange.UNKNOWN, description="최근 체중 변화")

    # 직업
    job = fields.CharField(max_length=100, null=True, description="직업")

    # 생활습관 - 흡연
    smoking_status = fields.CharEnumField(SmokingStatus, default=SmokingStatus.UNKNOWN, description="흡연 상태")
    smoking_years = fields.IntField(null=True, description="흡연 기간(년)")
    smoking_per_week = fields.FloatField(null=True, description="주 평균 흡연량(팀 기준 단위 통일)")

    # 생활습관 - 음주
    drinking_status = fields.CharEnumField(DrinkingStatus, default=DrinkingStatus.UNKNOWN, description="음주 상태")
    drinking_years = fields.IntField(null=True, description="음주 기간(년)")
    drinking_per_week = fields.FloatField(null=True, description="주 평균 음주량(팀 기준 단위 통일)")

    # 생활습관 - 운동/식습관 (enum)
    exercise_frequency = fields.CharEnumField(
        ExerciseFrequency, default=ExerciseFrequency.UNKNOWN, description="운동 빈도"
    )
    diet_type = fields.CharEnumField(DietType, default=DietType.UNKNOWN, description="식습관 유형")

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "health_profiles"
        table_description = "사용자 건강 프로필(정적/준정적 정보)"

    def __str__(self) -> str:
        return f"HealthProfile(user={getattr(self, 'user_id', 'N/A')})"
