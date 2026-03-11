from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.user import User


class LLMLifeGuide(models.Model):
    """
    AI가 생성한 환자 맞춤형 복약 및 생활 가이드 전문을 관리하는 모델입니다.
    생성 당시의 환자 상태와 긴급 알림 포함 여부를 기록합니다.
    """

    id = fields.IntField(pk=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField("models.User", related_name="life_guides")
    # 생성 시점의 환자 상태(기저질환+알러지+현재약물) 요약 (RAG Context)
    user_current_status = fields.TextField()
    # [대시보드 하단] AI가 생성한 맞춤 가이드 전문
    generated_content: fields.JSONField = fields.JSONField()
    activity = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "llm_life_guides"
