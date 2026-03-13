import logging
from typing import Any

from app.models.ocr_history import OCRHistory
from app.models.prescription import Prescription
from app.models.prescription_drug import PrescriptionDrug
from app.models.upload import Upload
from app.models.user import User

logger = logging.getLogger(__name__)


class PrescriptionRepository:
    """
    처방전(Prescription) 및 관련 약물 모델에 대한 데이터베이스 접근을 담당하는 리포지토리 클래스입니다.
    """

    async def create(
        self,
        user: User,
        upload: Upload,
        ocr_history: OCRHistory | None = None,
        hospital_name: str | None = None,
        prescribed_date: Any | None = None,
        drug_list_raw: str | None = None,
    ) -> Prescription:
        """
        새로운 처방전 분석 레코드를 생성합니다 (Step 3).
        """
        return await Prescription.create(  # type: ignore[no-any-return]
            user=user,
            upload=upload,
            ocr_history=ocr_history,
            hospital_name=hospital_name,
            prescribed_date=prescribed_date,
            drug_list_raw=drug_list_raw,
        )

    async def create_drug(
        self,
        prescription: Prescription,
        standard_drug_name: str,
        dosage_amount: float | None = None,
        daily_frequency: int | None = None,
        duration_days: int | None = None,
    ) -> PrescriptionDrug:
        """
        처방전에 포함된 개별 약물 레코드를 생성합니다 (Step 5).
        """
        return await PrescriptionDrug.create(  # type: ignore[no-any-return]
            prescription=prescription,
            standard_drug_name=standard_drug_name,
            dosage_amount=dosage_amount,
            daily_frequency=daily_frequency,
            duration_days=duration_days,
        )

    async def get_by_id(self, prescription_id: int) -> Prescription | None:
        """
        ID로 처방전 레코드를 조회합니다.
        """
        return await Prescription.filter(id=prescription_id).first()  # type: ignore[no-any-return]

    async def last_prescription(self, user: User):
        return await Prescription.filter(user=user).order_by("-created_at").first()
