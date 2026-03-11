import os
import re
import uuid
from datetime import datetime
from typing import Any

from fastapi import UploadFile

from app.models.user import User
from app.repositories.upload import UploadRepository
from app.services.llm_service import LLMService


class UploadService:
    def __init__(self):
        self._repo = UploadRepository()
        self.llm_service = LLMService()

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

    async def get_upload_file(self, user: Any | None) -> dict[str, Any]:
        """
        [C901 해결] 함수를 분리하여 복잡도를 낮췄습니다.
        """
        if not user:
            return {"status": "no_user", "content": {}}

        uploads = await self._repo.get_latest_day_uploads(user.id)
        if not uploads:
            return {"status": "no_data", "content": {}}

        # 그룹화 로직을 별도 메서드로 추출
        processed_results = self._process_pill_data(uploads)

        return await self.upload_pull_status(processed_results)

    def _get_base_name(self, path: str) -> str:
        """파일명에서 핵심 이름을 추출합니다."""
        filename = os.path.basename(path)
        name_no_ext = os.path.splitext(filename)[0]
        return re.sub(r"(_?front|_?back)$", "", name_no_ext, flags=re.IGNORECASE)

    def _process_pill_data(self, uploads: list[Any]) -> list[Any]:
        """
        [Mypy 에러 해결]
        1. groups의 타입을 Dict[str, Dict[str, Any]]로 명시하여 Tuple 에러 방지.
        2. getattr와 타입 체크를 통해 Attribute 에러 방지.
        """
        groups: dict[str, dict[str, Any]] = {}
        others: list[Any] = []

        # 1. 사진 그룹화
        for upload in uploads:
            if upload.category in ["pill_front", "pill_back"]:
                base = self._get_base_name(upload.file_path)
                if base not in groups:
                    # 초기화를 dict로 명확히 함
                    groups[base] = {"front": None, "back": None}

                if upload.category == "pill_front":
                    groups[base]["front"] = upload
                else:
                    groups[base]["back"] = upload
            else:
                others.append(upload)

        # 2. 그룹 병합
        results: list[Any] = []
        for group in groups.values():
            front = group["front"]
            back = group["back"]
            target = front or back

            if not target:
                continue

            # [Mypy] getattr를 사용하여 안전하게 속성 접근
            front_asset = getattr(front, "pill_front_asset", None) if front else None
            back_asset = getattr(back, "pill_back_asset", None) if back else None
            recognition = front_asset or back_asset

            if recognition:
                # [Mypy] front/back이 존재할 때만 file_path 접근
                if front:
                    recognition.front_file_path = front.file_path
                if back:
                    recognition.back_file_path = back.file_path
                target.pill_recognition = recognition

            target.category = "pill"
            results.append(target)

        results.extend(others)
        return results

    async def upload_pull_status(self, data: list) -> dict:
        """
        약물 상호작용 및 설명
        """
        # API 키가 없으면 더미 데이터 반환
        if not self.llm_service.client:
            # If API key is missing, return a dummy JSON directly to show the UI
            return {
                "status": "API Key Missing",
                "content": {
                    "interaction": "서비스 점검 중",
                    "pill_list": [],
                    "disclaimer": "API 키가 설정되지 않았습니다.",
                },
            }

        pill_list = []
        for row in data:
            # 약 이름 추출 로직 (기존과 동일)
            if row.category == "prescription" and row.prescription:
                for drug in row.prescription.drugs:
                    if drug.standard_drug_name:
                        pill_list.append(drug.standard_drug_name)
            elif getattr(row, "pill_recognition", None):
                if row.pill_recognition.pill_name:
                    pill_list.append(row.pill_recognition.pill_name)

        pill_list = list(set(pill_list))

        if not pill_list:
            return {
                "status": "EMPTY_PILLS",
                "content": {"interaction": "분석할 약물이 없습니다.", "pill_list": [], "disclaimer": ""},
            }

        prompt = f"""
    약사로서 약물에 대한 상호작용 또는 약물에 대한 설명을 해줘


    [알약 목록]
    {", ".join(pill_list) if pill_list else "없음"}

    [작성 규칙]
    1. severity_display: UI 배지에 노출할 단어 (안전/주의/위험 중 하나).
    2. summary: 사용자가 가장 먼저 읽어야 할 핵심 상호작용 결과를 20자 이내로 작성.
    3. pill_names: 분석된 약물 이름을 쉼표로 나열.

    [응답 JSON 구조]
    {{
        "severity_display": "주의",
        "summary": "혈압 수치 변화에 유의하세요",
        "pill_names": "타이레놀정", "아모디핀정"
    }}
    """.strip()

        try:
            content_json = await self.llm_service.generate_json(
                messages=[
                    {
                        "role": "system",
                        "content": "약사로서 약물에 대한 상호작용 또는 약물에 대한 설명한다. JSON 형식으로만 답변한다.",
                    },
                    {"role": "user", "content": prompt},
                ],
                model="gpt-4o-mini",
                temperature=0.4,
            )

            return {
                "status": "success",
                "content": content_json,
            }
        except Exception as e:
            return {
                "status": "error",
                "content": {"interaction": "분석 중 오류 발생", "pill_list": [], "disclaimer": str(e)},
            }
