from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.logger import default_logger
from app.dependencies.security import get_request_user
from app.models.user import User
from app.services.ocr import OCRService

analysis_router = APIRouter(prefix="/analysis", tags=["analysis"])


@analysis_router.post("/prescriptions", status_code=status.HTTP_201_CREATED)
async def analyze_prescription(
    upload_id: int,
    user: Annotated[User, Depends(get_request_user)],
    ocr_service: Annotated[OCRService, Depends(OCRService)],
):
    """
    [ANALYSIS] 처방전 분석(OCR->정제).
    ocr_history + prescriptions + prescription_drugs 생성
    """
    default_logger.info("[Analysis] analyze_prescription - 로그인")
    # Simply mapping to service logic (simplified for specs)
    # In reality, service would fetch upload_id file and do OCR
    return {
        "ocr_history_id": 1,
        "prescription_id": 101,
        "hospital_name": "서울대학교병원",
        "prescribed_date": "2024-02-24",
        "drugs": [
            {
                "id": 501,
                "standard_drug_name": "타이레놀",
                "dosage_amount": 500.0,
                "daily_frequency": 3,
                "duration_days": 3,
                "is_linked_to_meds": False,
            }
        ],
    }


@analysis_router.post("/pills", status_code=status.HTTP_201_CREATED)
async def analyze_pills(
    user: Annotated[User, Depends(get_request_user)],
    front_upload_id: int,
    back_upload_id: int | None = None,
):
    """
    [ANALYSIS] 알약 복합 분석(CNN+OCR).
    AI 불확실성 대비 candidates 반환
    """
    default_logger.info("[Analysis] analyze_pills - 로그인")
    return {
        "cnn_history_id": 2,
        "ocr_history_id": 3,
        "pill_recognition_id": 201,
        "primary_pill_name": "아스피린",
        "confidence": 0.98,
        "candidates": [{"pill_name": "아스피린", "confidence": 0.98}, {"pill_name": "부르펜", "confidence": 0.02}],
    }
