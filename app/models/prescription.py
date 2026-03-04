from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.upload import Upload
    from app.models.user import User


class Prescription(models.Model):
    """
    사용자가 업로드한 처방전의 분석 결과를 관리하는 모델입니다.
    병원 정보, 처방 일자 및 원본 업로드 이력과 연결됩니다.
    """

    id = fields.IntField(pk=True)
    hospital_name = fields.CharField(max_length=255, null=True)  # 정제된 병원 이름
    prescribed_date = fields.DateField(null=True)  # 정제된 처방 일자
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField("models.User", related_name="prescriptions")
    # 1개의 이미지는 1개의 처방전 결과 (1:1)
    upload: fields.OneToOneRelation["Upload"] = fields.OneToOneField("models.Upload", related_name="prescription")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "prescriptions"
