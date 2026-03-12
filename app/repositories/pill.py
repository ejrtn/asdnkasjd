import logging
from typing import Any

from app.models.ocr_history import OCRHistory
from app.models.pill_recognitions import PillRecognition
from app.models.upload import Upload
from app.models.user import User

logger = logging.getLogger(__name__)


class PillRepository:
    """
    알약 식별(PillRecognition) 및 관련 히스토리(OCRHistory) 레코드 생성을 담당하는 리포지토리입니다.
    """

    async def create_history(
        self,
        user: User,
        front_upload: Upload,
        back_upload: Upload | None,
        raw_text: str = "",
    ) -> OCRHistory:
        """
        OCRHistory 레코드를 생성합니다.
        """
        return await OCRHistory.create(  # type: ignore[no-any-return]
            user=user,
            raw_text=raw_text,
            is_valid=True if raw_text.strip() else False,
            front_upload=front_upload,
            back_upload=back_upload,
        )

    async def create_recognition(
        self,
        user: User,
        pill_name: str,
        pill_description: str,
        front_upload: Upload,
        back_upload: Upload | None,
        confidence: float = 0.0,
        cnn_result: dict[str, Any] | None = None,
        model_version: str = "gpt-4o-mini-vision",
    ) -> PillRecognition:
        """
        최종 알약 식별 레코드를 생성합니다. (CNN 분석 결과 포함)
        """
        return await PillRecognition.create(  # type: ignore[no-any-return]
            user=user,
            pill_name=pill_name,
            pill_description=pill_description,
            front_upload=front_upload,
            back_upload=back_upload,
            confidence=confidence,
            raw_result=cnn_result,
            model_version=model_version,
        )
