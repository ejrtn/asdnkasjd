import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.dependencies.security import get_request_user
from app.models.ocr_history import OCRHistory
from app.models.upload import Upload
from app.models.user import User
from app.services.ocr import OCRService

ocr_router = APIRouter(prefix="/ocr", tags=["ocr"], dependencies=[Depends(get_request_user)])
ocr_service = OCRService()

# 업로드 디렉토리 설정
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def save_file(file: UploadFile, user: User, category: str) -> Upload:
    """
    파일 유효성 검사, 물리적 저장 및 Upload 레코드 생성을 담당하는 공통 함수입니다.
    """
    allowed_extensions = {".pdf", ".png", ".jpg", ".jpeg"}
    file_ext = os.path.splitext(file.filename or "")[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"허용되지 않은 파일 형식입니다. (허용: {sorted(allowed_extensions)})",
        )

    # 1. 파일 이름 UUID 변환 및 경로 설정
    content = await file.read()
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # 2. 물리적 파일 저장
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"파일 저장 중 오류 발생: {str(e)}"
        ) from e

    # 3. DB Upload 레코드 생성
    return await Upload.create(  # type: ignore[no-any-return]
        user=user,
        original_name=file.filename,
        file_path=file_path,
        file_type=file.content_type or "image/jpeg",
        category=category,
    )


@ocr_router.post("/prescription", status_code=status.HTTP_201_CREATED)
async def extract_prescription_ocr(
    file: Annotated[UploadFile, File()],
    user: Annotated[User, Depends(get_request_user)],
):
    """
    [OCR] 처방전 이미지/PDF 업로드 및 텍스트 추출
    """
    # 1. 파일 저장 및 DB 등록
    upload_record = await save_file(file, user, category="prescription")

    # 2. OCR 실행
    # OCRService 내부에서 에러 시 HTTPException 발생
    with open(upload_record.file_path, "rb") as f:
        image_bytes = f.read()

    filename = upload_record.original_name or "prescription.jpg"
    file_ext = os.path.splitext(filename)[1] or ".jpg"

    raw_text = await ocr_service.extract_raw_text(image_bytes=image_bytes, file_name=filename, file_ext=file_ext)

    # 3. OCRHistory 저장
    ocr_record = await OCRHistory.create(
        user=user,
        raw_text=raw_text,
        front_upload=upload_record,
        back_upload=None,
        is_valid=True if raw_text.strip() else False,
    )

    return {
        "ocr_id": ocr_record.id,
        "is_valid": ocr_record.is_valid,
        "preview_text": raw_text[:50] + "..." if len(raw_text) > 50 else raw_text,
        "message": "처방전 분석 완료",
    }


@ocr_router.post("/pill", status_code=status.HTTP_201_CREATED)
async def extract_pill_ocr(
    front_file: Annotated[UploadFile, File()],
    back_file: Annotated[UploadFile, File()],
    user: Annotated[User, Depends(get_request_user)],
):
    """
    [OCR] 알약 앞/뒷면 이미지 업로드 및 텍스트 추출
    """
    # 1. 각각의 파일 저장
    front_upload = await save_file(front_file, user, category="pill_front")
    back_upload = await save_file(back_file, user, category="pill_back")

    # 2. OCR 실행 (앞면과 뒷면 결과 병합)
    combined_text = ""

    # 앞면 OCR
    with open(front_upload.file_path, "rb") as f:
        front_bytes = f.read()
    front_text = await ocr_service.extract_raw_text(
        image_bytes=front_bytes,
        file_name=front_upload.original_name or "front.jpg",
        file_ext=os.path.splitext(front_upload.original_name or ".jpg")[1],
    )

    # 뒷면 OCR
    with open(back_upload.file_path, "rb") as f:
        back_bytes = f.read()
    back_text = await ocr_service.extract_raw_text(
        image_bytes=back_bytes,
        file_name=back_upload.original_name or "back.jpg",
        file_ext=os.path.splitext(back_upload.original_name or ".jpg")[1],
    )

    combined_text = f"[Front] {front_text}\n[Back] {back_text}"

    # 3. OCRHistory 저장 (앞/뒤 모두 연결)
    ocr_record = await OCRHistory.create(
        user=user,
        raw_text=combined_text,
        front_upload=front_upload,
        back_upload=back_upload,
        is_valid=True if front_text.strip() or back_text.strip() else False,
    )

    return {
        "ocr_id": ocr_record.id,
        "is_valid": ocr_record.is_valid,
        "preview_text": combined_text[:50] + "..." if len(combined_text) > 50 else combined_text,
        "message": "알약 분석 완료",
    }
