from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.user import User


class ChronicDisease(models.Model):
    """
    사용자가 앓고 있는 기저 질환(고혈압, 당뇨 등) 정보를 관리하는 모델입니다.
    AI 건강 가이드 생성 시 환자의 기저 상태를 파악하는 맥락으로 활용됩니다.
    """

    id = fields.IntField(pk=True)
    disease_name = fields.CharField(max_length=100)  # 질환명 (예: 고혈압, 당뇨)
    when_to_diagnose = fields.CharField(max_length=10)  # 진단 시기 (YYYY-MM-DD 형식)
    # 사용자별 기저질환 관리 (N:1)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField("models.User", related_name="chronic_diseases")

    class Meta:
        table = "chronic_diseases"
