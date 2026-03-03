from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.current_med import CurrentMed
    from app.models.user import User


class Alarm(models.Model):
    """
    사용자가 설정한 알람 정보를 관리하는 모델입니다.
    alarm_type으로 복약/혈압/혈당 알람을 구분합니다.

    alarm_type 종류:
    - MED        : 복약 알람 (current_med FK 연결)
    - BP_MORNING : 혈압 아침 측정 알람 (기상 후 1시간 내)
    - BP_EVENING : 혈압 저녁 측정 알람 (잠들기 전)
    - BS_FASTING : 혈당 공복 측정 알람
    - BS_POSTMEAL: 혈당 식후 2시간 측정 알람
    - BS_BEDTIME : 혈당 취침 전 측정 알람
    """

    id = fields.IntField(pk=True)
    alarm_type = fields.CharField(max_length=20, default="MED")  # 알람 종류
    alarm_time = fields.TimeField()  # 알람 시간
    is_active = fields.BooleanField(default=True)  # 알람 활성화 여부
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField("models.User", related_name="alarms")
    current_med: fields.ForeignKeyRelation["CurrentMed"] | None = fields.ForeignKeyField(
        "models.CurrentMed",
        related_name="alarms",
        null=True,  # MED 타입일 때만 연결, 혈압/혈당은 null
    )

    class Meta:
        table = "alarms"
