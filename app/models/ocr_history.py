from tortoise import fields, models


class OCRHistory(models.Model):
    """
    이미지 내 텍스트 추출(OCR) 엔진의 분석 원본 이력을 관리하는 모델입니다.
    추출된 가공되지 않은 전체 텍스트와 엔진 메타데이터를 포함합니다.
    """

    id = fields.IntField(pk=True)
    # [중요] 처방전 글자 혹은 알약 표면의 각인(문자/숫자) 원본 결과
    raw_text = fields.TextField()
    inference_metadata = fields.JSONField(null=True)  # 분석 소요 시간, 모델 버전 등
    created_at = fields.DatetimeField(auto_now_add=True)
    front_upload = fields.OneToOneField("models.Upload", related_name="ocr_histories_front")
    back_upload = fields.OneToOneField("models.Upload", related_name="ocr_histories_back")
    user = fields.ForeignKeyField("models.User", related_name="ocr_histories")

    class Meta:
        table = "ocr_history"
