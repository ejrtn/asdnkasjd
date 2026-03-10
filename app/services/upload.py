import os
import uuid
from datetime import datetime

from fastapi import UploadFile

from app.models.user import User
from app.repositories.upload import UploadRepository


class UploadService:
    def __init__(self):
        self._repo = UploadRepository()

    async def file_save(self, user: User, files: list[UploadFile]):
        upload_dir = "/app/uploads"

        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        os.makedirs(upload_dir, exist_ok=True)

        uploaded_results = []

        for file in files:
            # 1. 파일명 및 확장자 추출
            filename = file.filename or "unknown"
            name = os.path.splitext(filename)[0]
            file_ext = os.path.splitext(filename)[1]
            unique_filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{uuid.uuid4()}_{name}{file_ext}"
            file_path = os.path.join(upload_dir, unique_filename)

            # 2. 실제 파일 저장
            content = await file.read()
            with open(file_path, "wb") as buffer:
                buffer.write(content)

            # 3. 결과 리스트에 추가
            uploaded_results.append(
                {"file_path": f"/uploads/{unique_filename}", "original_name": filename, "file_type": file.content_type}
            )

        await self._repo.create_file(user.id, uploaded_results)

        # 모든 파일 업로드 결과 반환
        return uploaded_results
