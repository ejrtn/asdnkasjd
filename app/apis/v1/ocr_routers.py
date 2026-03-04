import os
from typing import Annotated

from fastapi import APIRouter, File, UploadFile, status

from app.services.ocr import OCRService

ocr_router = APIRouter(prefix="/ocr", tags=["ocr"])
ocr_service = OCRService()


@ocr_router.post("", status_code=status.HTTP_200_OK)
async def extract_ocr_text(
    file: Annotated[UploadFile, File()],
):
    """
    [OCR] 이미지 파일에서 텍스트 추출 (Naver Clova OCR 연동)
    """
    content = await file.read()
    filename = file.filename or "uploaded_image.jpg"
    file_ext = os.path.splitext(filename)[1] or ".jpg"

    raw_text = await ocr_service.extract_raw_text(image_bytes=content, file_name=filename, file_ext=file_ext)

    return {"raw_text": raw_text}
