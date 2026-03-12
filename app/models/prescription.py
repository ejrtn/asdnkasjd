from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.ocr_history import OCRHistory
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
    # [Step 3] LLM이 파싱한 약물 이름들의 원본 리스트 (쉼표 등으로 구분된 문자열)
    drug_list_raw = fields.TextField(null=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField("models.User", related_name="prescriptions")
    # 1개의 이미지는 1개의 처방전 결과 (1:1)
    upload: fields.OneToOneRelation["Upload"] = fields.OneToOneField("models.Upload", related_name="prescription")
    # OCR 원본 이력과의 1:1 연결
    ocr_history: fields.OneToOneRelation["OCRHistory"] | None = fields.OneToOneField(
        "models.OCRHistory", related_name="prescription", null=True
    )
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "prescriptions"
