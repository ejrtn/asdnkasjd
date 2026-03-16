from typing import TYPE_CHECKING, Any

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.current_med import CurrentMed
    from app.models.upload import Upload
    from app.models.user import User


class PillRecognition(models.Model):
    """
    AI 모델을 통한 알약 외형 이미지 분석 이력을 관리하는 모델입니다.
    분석에 사용된 모델 버전, 식별된 클래스 및 신뢰도(Confidence)를 기록합니다.
    """

    id = fields.IntField(pk=True)
    model_version = fields.CharField(max_length=50, null=True)
    pill_name = fields.CharField(max_length=255)
    pill_description = fields.TextField(null=True)  # 약의 상세 효능 및 주의사항
    confidence = fields.FloatField()  # AI의 확신도 (예: 0.98)
    raw_result: Any = fields.JSONField(null=True)  # 분석 엔진의 전체 결과 데이터
    created_at = fields.DatetimeField(auto_now_add=True)
    front_upload: fields.ForeignKeyRelation["Upload"] = fields.ForeignKeyField(
        "models.Upload", related_name="pill_recognitions_front", null=True
    )
    back_upload: fields.ForeignKeyRelation["Upload"] | None = fields.ForeignKeyField(
        "models.Upload", related_name="pill_recognitions_back", null=True
    )

    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField("models.User", related_name="pill_recognitions")

    # CurrentMed와 1:1 관계 (식별된 결과가 실제 복용 목록에 추가될 때 사용)
    current_med: fields.OneToOneRelation["CurrentMed"]

    class Meta:
        table = "pill_recognitions"
