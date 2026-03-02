from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.current_med import CurrentMed
    from app.models.user import User


class Alarm(models.Model):
    """
    사용자가 설정한 정기적인 복약 알림 정보를 관리하는 모델입니다.
    CurrentMed와 연동하여 각 약물마다 알림을 설정할 수 있습니다.
    """

    id = fields.IntField(pk=True)
    alarm_time = fields.TimeField()
    is_active = fields.BooleanField(default=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField("models.User", related_name="alarms")
    current_med: fields.ForeignKeyRelation["CurrentMed"] = fields.ForeignKeyField(
        "models.CurrentMed", related_name="alarms", null=True
    )

    class Meta:
        table = "alarms"
