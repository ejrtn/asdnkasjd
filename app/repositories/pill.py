import logging
from typing import Any

from app.models.cnn_history import CNNHistory
from app.models.ocr_history import OCRHistory
from app.models.pill_recognition import PillRecognition
from app.models.upload import Upload
from app.models.user import User

logger = logging.getLogger(__name__)


class PillRepository:
    """
    알약 식별(PillRecognition) 및 관련 히스토리(CNNHistory, OCRHistory) 레코드 생성을 담당하는 리포지토리입니다.
    """

    async def create_history(
        self,
        user: User,
        front_upload: Upload,
        back_upload: Upload | None,
        raw_text: str = "",
        cnn_result: dict[str, Any] | None = None,
        confidence: float = 0.0,
        model_version: str = "gpt-4o-mini-vision",
    ) -> tuple[OCRHistory, CNNHistory]:
        """
        OCRHistory와 CNNHistory 레코드를 동시에 생성합니다.
        """
        ocr_history = await OCRHistory.create(
            user=user,
            raw_text=raw_text,
            is_valid=True if raw_text.strip() else False,
            front_upload=front_upload,
            back_upload=back_upload,
        )

        cnn_history = await CNNHistory.create(
            user=user,
            model_version=model_version,
            confidence=confidence,
            raw_result=cnn_result,
            front_upload=front_upload,
            back_upload=back_upload,
        )

        return ocr_history, cnn_history

    async def create_recognition(
        self,
        user: User,
        pill_name: str,
        pill_description: str,
        ocr_history: OCRHistory,
        cnn_history: CNNHistory,
        front_upload: Upload,
        back_upload: Upload | None,
    ) -> PillRecognition:
        """
        최종 알약 식별 레코드를 생성합니다.
        """
        return await PillRecognition.create(  # type: ignore[no-any-return]
            user=user,
            pill_name=pill_name,
            pill_description=pill_description,
            ocr_history=ocr_history,
            cnn_history=cnn_history,
            front_upload=front_upload,
            back_upload=back_upload,
        )
