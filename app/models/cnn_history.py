from tortoise import fields, models


class CNNHistory(models.Model):
    """
    AI 모델을 통한 알약 외형 이미지 분석 이력을 관리하는 모델입니다.
    분석에 사용된 모델 버전, 식별된 클래스 및 신뢰도(Confidence)를 기록합니다.
    """

    id = fields.IntField(pk=True)
    model_version = fields.CharField(max_length=50, null=True)
    confidence = fields.FloatField()  # AI의 확신도 (예: 0.98)
    raw_result = fields.JSONField(null=True)  # 분석 엔진의 전체 결과 데이터
    created_at = fields.DatetimeField(auto_now_add=True)
    front_upload = fields.OneToOneField("models.Upload", related_name="cnn_histories_front")
    back_upload = fields.OneToOneField("models.Upload", related_name="cnn_histories_back")

    user = fields.ForeignKeyField("models.User", related_name="cnn_histories")

    class Meta:
        table = "cnn_history"
