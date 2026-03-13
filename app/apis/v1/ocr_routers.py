import logging
import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.dependencies.security import get_request_user
from app.models.upload import Upload
from app.models.user import User
from app.repositories.pill import PillRepository
from app.services.ocr import OCRService
from app.services.prescription import PrescriptionService

logger = logging.getLogger(__name__)

ocr_router = APIRouter(prefix="/ocr", tags=["ocr"], dependencies=[Depends(get_request_user)])
ocr_service = OCRService()
prescription_service = PrescriptionService()
pill_repo = PillRepository()

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


@ocr_router.get("/last-prescription", status_code=status.HTTP_201_CREATED)
async def last_prescription(
    user: Annotated[User, Depends(get_request_user)],
):
    return await ocr_service.last_prescription(user)


@ocr_router.post("/prescription", status_code=status.HTTP_201_CREATED)
async def extract_prescription_ocr(
    file: Annotated[UploadFile, File()],
    user: Annotated[User, Depends(get_request_user)],
):
    """
    [OCR] 처방전 이미지/PDF 업로드 및 Vision 기반 데이터 추출
    """
    # 1. 파일 저장 및 DB 등록
    upload_record = await save_file(file, user, category="prescription")

    # 2. 파일 바이트 읽기
    with open(upload_record.file_path, "rb") as f:
        image_bytes = f.read()

    # 3. Vision 기반 분석 실행 (OCR + LLM 파싱 통합)
    parsed_prescription = None
    drugs = []
    try:
        parsed_prescription = await prescription_service.process_prescription_vision_parsing(
            user=user, upload=upload_record, image_bytes=image_bytes
        )

        if parsed_prescription:
            # 연관된 약물 목록 가져오기
            drugs = await parsed_prescription.drugs.all()
    except Exception as e:
        logger.error(f"Vision 처방전 파싱 실패 (Upload ID: {upload_record.id}): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"처방전 분석 중 오류 발생: {str(e)}"
        ) from e

    return {
        "prescription_id": parsed_prescription.id if parsed_prescription else None,
        "hospital_name": parsed_prescription.hospital_name if parsed_prescription else None,
        "prescribed_date": parsed_prescription.prescribed_date if parsed_prescription else None,
        "drug_list_raw": parsed_prescription.drug_list_raw if parsed_prescription else None,
        "drug_names": (
            [name.strip() for name in parsed_prescription.drug_list_raw.split(",") if name.strip()]
            if parsed_prescription and parsed_prescription.drug_list_raw
            else []
        ),
        "drugs": [
            {
                "id": d.id,
                "standard_drug_name": d.standard_drug_name,
                "dosage": d.dosage_amount,
                "frequency": d.daily_frequency,
                "duration": d.duration_days,
            }
            for d in drugs
        ],
        "message": "처방전 Vision 분석 완료",
    }


class PillSyncRequest(BaseModel):
    drug_names: list[str] | None = None


@ocr_router.post("/prescriptions/{prescription_id}/sync", status_code=status.HTTP_200_OK)
async def sync_prescription_meds(
    prescription_id: int,
    request: PillSyncRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    """
    처방전의 데이터를 현재 복용 내역으로 연동합니다.
    사용자가 선택한 약물 리스트(drug_names)가 있다면 해당 약물만 연동합니다.
    """
    try:
        created_meds = await prescription_service.sync_to_current_meds(
            prescription_id=prescription_id, user=user, drug_names=request.drug_names
        )
        return {
            "success": True,
            "count": len(created_meds),
            "message": f"{len(created_meds)}개의 약물이 현재 복용 목록에 추가되었습니다.",
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error(f"약물 연동 에러: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="약물 연동 중 오류가 발생했습니다."
        ) from e


@ocr_router.post("/pill", status_code=status.HTTP_201_CREATED)
async def extract_pill_ocr(
    front_file: Annotated[UploadFile, File()],
    back_file: Annotated[UploadFile, File()],
    user: Annotated[User, Depends(get_request_user)],
):
    """
    [OCR] 알약 앞/뒷면 이미지 업로드 및 LLM 기반 식별
    """
    # 1. 파일 저장
    front_upload = await save_file(front_file, user, category="pill_front")
    back_upload = await save_file(back_file, user, category="pill_back")

    # 2. 파일 바이트 읽기
    with open(front_upload.file_path, "rb") as f:
        front_bytes = f.read()
    with open(back_upload.file_path, "rb") as f:
        back_bytes = f.read()

    # 3. LLM 기반 알약 식별 실행
    pill_data = await ocr_service.identify_pill_with_llm(front_bytes, back_bytes)

    # 4. 히스토리 및 식별 레코드 저장
    # user 요청 사항: 보여지는 텍스트(display_text)를 CNNHistory.raw_result에 저장
    await pill_repo.create_history(
        user=user,
        front_upload=front_upload,
        back_upload=back_upload,
        raw_text=pill_data.get("name", ""),
    )

    recognition = await pill_repo.create_recognition(
        user=user,
        pill_name=pill_data.get("name", "알 수 없는 약품"),
        pill_description=pill_data.get("efficacy", ""),
        front_upload=front_upload,
        back_upload=back_upload,
        cnn_result=pill_data,  # 전체 결과를 저장 (display_text 포함)
        confidence=pill_data.get("confidence", 0.0),
    )

    return {
        "id": recognition.id,
        "name": pill_data.get("name"),
        "efficacy": pill_data.get("efficacy"),
        "appearance": pill_data.get("appearance"),
        "caution": pill_data.get("caution"),
        "display_text": pill_data.get("display_text"),
        "candidates": pill_data.get("candidates", []),
        "message": "알약 분석 완료",
    }


@ocr_router.post("/pill/select", status_code=status.HTTP_200_OK)
async def select_pill_candidate(
    recognition_id: Annotated[int, Form()],
    pill_name: Annotated[str, Form()],
    pill_description: Annotated[str, Form()],
    user: Annotated[User, Depends(get_request_user)],
):
    """
    사용자가 여러 후보 중 최종적으로 선택한 알약 정보를 업데이트합니다.
    """
    from app.models.pill_recognitions import PillRecognition

    recognition = await PillRecognition.get_or_none(id=recognition_id, user=user)
    if not recognition:
        raise HTTPException(status_code=404, detail="식별 레코드를 찾을 수 없습니다.")

    recognition.pill_name = pill_name
    recognition.pill_description = pill_description
    await recognition.save()

    return {"message": "알약 정보가 업데이트되었습니다.", "pill_name": pill_name}
