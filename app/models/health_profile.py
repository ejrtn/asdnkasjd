from enum import Enum
from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.user import User


class FamilyHistory(str, Enum):
    NO = "없음"
    MAN = "부 있음"
    WOMAN = "모 있음"
    MANWOMAN = "부모 있음"
    UNKNOWN = "모름"


class SmokingStatus(str, Enum):
    NEVER = "비흡연"
    CURRENT = "흡연"
    FORMER = "과거 흡연"


class DrinkingStatus(str, Enum):
    NEVER = "비음주"
    CURRENT = "음주"
    FORMER = "과거 음주"


class WeightChange(str, Enum):
    NO_CHANGE = "변화없음"
    GAIN = "증가"
    LOSS = "감소"
    UNKNOWN = "모름"


class SleepChange(str, Enum):
    NO_CHANGE = "변화없음"
    GAIN = "증가"
    LOSS = "감소"
    UNKNOWN = "모름"


class ExerciseFrequency(str, Enum):
    NONE = "안함"
    WEEK_1_2 = "주 1~2회"
    WEEK_3_OR_MORE = "주 3회 이상"


class DietType(str, Enum):
    BALANCED = "균형 잡힌"
    LOW_SALT = "저염"
    LOW_CARB = "저탄수화물"
    HIGH_PROTEIN = "고단백"
    VEGETARIAN = "채식"
    IRREGULAR = "불규칙적"
    FAST_FOOD = "패스트푸드"
    UNKNOWN = "모름"


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
    family_history = fields.CharEnumField(FamilyHistory, description="가족력")
    family_history_note = fields.TextField(null=True, description="사용자 입력 텍스트")

    # 신체계측(팀 합의: 체중은 프로필에 포함)
    height_cm = fields.FloatField(description="신장(cm)")
    weight_kg = fields.FloatField(description="체중(kg)")
    weight_change = fields.CharEnumField(WeightChange, description="최근 체중 변화")

    # 수면
    sleep_hours = fields.FloatField(null=True, description="수면 시간(시간)")
    sleep_change = fields.CharEnumField(SleepChange, description="최근 수면 변화")

    # 생활습관 - 흡연
    smoking_status = fields.CharEnumField(SmokingStatus, description="흡연 상태")
    smoking_years = fields.IntField(null=True, description="흡연 기간(년)")
    smoking_per_week = fields.FloatField(null=True, description="주 평균 흡연량(팀 기준 단위 통일)")

    # 생활습관 - 음주
    drinking_status = fields.CharEnumField(DrinkingStatus, description="음주 상태")
    drinking_years = fields.IntField(null=True, description="음주 기간(년)")
    drinking_per_week = fields.FloatField(null=True, description="주 평균 음주량(팀 기준 단위 통일)")

    # 생활습관 - 운동/식습관 (enum)
    exercise_frequency = fields.CharEnumField(ExerciseFrequency, description="운동 빈도")
    diet_type = fields.CharEnumField(DietType, description="식습관 유형")

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "health_profiles"
        table_description = "사용자 건강 프로필(정적/준정적 정보)"

    def __str__(self) -> str:
        return f"HealthProfile(user={getattr(self, 'user_id', 'N/A')})"
