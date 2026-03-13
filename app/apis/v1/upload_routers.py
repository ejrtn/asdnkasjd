from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.dependencies.security import get_request_user
from app.dtos.upload import LatestDayUploadsResponse
from app.models.user import User
from app.services.upload import UploadService

upload_router = APIRouter(prefix="/uploads", tags=["upload"])


@upload_router.post("", status_code=status.HTTP_201_CREATED)
async def upload_file(
    user: Annotated[User, Depends(get_request_user)],
    files: list[UploadFile] = File(...),  # noqa: B008
):
    """
    [UPLOAD] 이미지 업로드(처방전/알약 앞/뒤)
    """
    upload_service = UploadService()
    return await upload_service.file_save(user, files)


@upload_router.get("", response_model=LatestDayUploadsResponse)
async def get_upload_file(user: Annotated[User, Depends(get_request_user)]):
    """
    [UPLOAD] 최근 데이터 day일 가져오기 및 AI 분석 결과 반환
    """
    upload_service = UploadService()
    return await upload_service.get_upload_file(user)


@upload_router.get("/history")
async def get_upload_history(user: Annotated[User, Depends(get_request_user)]):
    """
    [UPLOAD] 사용자의 전체 업로드 히스토리 조회
    """
    upload_service = UploadService()
    history = await upload_service.get_upload_history(user)
    return {"status": "success", "content": history}


@upload_router.delete("/{upload_id}")
async def delete_upload(upload_id: int, user: Annotated[User, Depends(get_request_user)]):
    """
    [UPLOAD] 특정 업로드 레코드 삭제
    """
    upload_service = UploadService()
    success = await upload_service.delete_upload_file(user, upload_id)
    if success:
        return {"status": "success", "message": "파일이 삭제되었습니다."}
    from fastapi import HTTPException

    raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
