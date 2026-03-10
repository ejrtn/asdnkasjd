from typing import TYPE_CHECKING, Any

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.upload import Upload
    from app.models.user import User


class OCRHistory(models.Model):
    """
    이미지 내 텍스트 추출(OCR) 엔진의 분석 원본 이력을 관리하는 모델입니다.
    추출된 가공되지 않은 전체 텍스트와 엔진 메타데이터를 포함합니다.
    """

    id = fields.IntField(pk=True)
    # [중요] 처방전 글자 혹은 알약 표면의 각인(문자/숫자) 원본 결과
    raw_text = fields.TextField()
    is_valid = fields.BooleanField(default=False)  # 유효한 데이터일 때 True
    inference_metadata: Any = fields.JSONField(null=True)  # 분석 소요 시간, 모델 버전 등
    created_at = fields.DatetimeField(auto_now_add=True)
    front_upload: fields.OneToOneRelation["Upload"] = fields.OneToOneField(
        "models.Upload", related_name="ocr_histories_front"
    )
    back_upload: fields.OneToOneRelation["Upload"] | None = fields.OneToOneField(
        "models.Upload", related_name="ocr_histories_back", null=True
    )
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField("models.User", related_name="ocr_histories")

    class Meta:
        table = "ocr_history"
