import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.dependencies.security import get_request_user
from app.models.upload import Upload
from app.models.user import User

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

upload_router = APIRouter(prefix="/uploads", tags=["upload"])


@upload_router.post("", status_code=status.HTTP_201_CREATED)
async def upload_file(
    user: Annotated[User, Depends(get_request_user)],
    file: Annotated[UploadFile, File()],
):
    """
    [UPLOAD] 이미지 업로드(처방전/알약 앞/뒤)
    """

    filename = file.filename or "unknown.jpg"
    file_ext = os.path.splitext(filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"

    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # ✅ 실제 파일 저장
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    upload_record = await Upload.create(
        user=user,
        original_name=file.filename,
        file_path=file_path,
        file_type=file.content_type or "image/jpeg",
    )

    return {
        "upload_id": upload_record.id,
        "file_url": f"/uploads/{unique_filename}",
    }
