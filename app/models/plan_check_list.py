from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.user import User


class PlanCheckList(models.Model):
    """
    오늘 계획 체크 리스트
    """

    id = fields.IntField(pk=True)
    content = fields.CharField(max_length=255)
    plan_type = fields.CharField(max_length=20, default="self")  # 'llm', 'pill', 'self'
    is_completed = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField("models.User", related_name="plan_check_list")

    class Meta:
        table = "plan_check_list"
