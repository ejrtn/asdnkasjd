from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.user import User


class Allergy(models.Model):
    """
    사용자가 보유한 알러지 성분 정보를 관리하는 모델입니다.
    가이드 생성 시 약물 상호작용 및 부작용 경고를 위한 기초 자료로 사용됩니다.
    """

    id = fields.IntField(pk=True)
    allergy_type = fields.CharField(max_length=100, null=True)
    allergy_name = fields.CharField(max_length=100, null=True)  # 라우터에서 사용하는 필드명
    symptom = fields.CharField(max_length=100, null=True)

    # 사용자별 알러지 관리 (N:1)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField("models.User", related_name="allergies")

    class Meta:
        table = "allergies"
