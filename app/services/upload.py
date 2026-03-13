import base64
import os
import re
import uuid
from pathlib import Path
from typing import Any

import anyio
import pandas as pd
from fastapi import UploadFile

from app.repositories.upload import UploadRepository
from app.services.llm_service import LLMService


class UploadService:
    UPLOAD_DIR = "/app/uploads/"
    CHROMA_DB_PATH = "./data/chroma_db"
    CSV_PATH = "app/data/docs/nedrug_data.csv"
    EMBEDDING_MODEL = "text-embedding-3-small"
    VISION_MODEL = "gpt-4o-mini"
    COLLECTION_NAME = "pill_database"

    def __init__(self):
        self._repo = UploadRepository()
        self.llm_service = LLMService()

        # CSV 로드 및 데이터 정제
        if os.path.exists(self.CSV_PATH):
            self.db_df = pd.read_csv(self.CSV_PATH, encoding="utf-8-sig", low_memory=False)
            # 검색 성능을 위해 결측치를 빈 문자열로 대체하고 대문자로 통일
            self.db_df["표시앞"] = self.db_df["표시앞"].fillna("").astype(str).str.upper()
            self.db_df["표시뒤"] = self.db_df["표시뒤"].fillna("").astype(str).str.upper()
            self.db_df["성상"] = self.db_df["성상"].fillna("").astype(str)
            self.db_df["색상앞"] = self.db_df["색상앞"].fillna("").astype(str)
            self.db_df["제형코드명"] = self.db_df["제형코드명"].fillna("").astype(str)
            print(f"✅ DB Loaded: {len(self.db_df)} rows")
        else:
            print(f"⚠️ Warning: CSV not found at {self.CSV_PATH}")

        # 1. 약학정보원 기준 색상 그룹화 (대표색 기준 통합)
        self.COLOR_GROUPS = {
            "하양": ["백색", "투명", "무색"],
            "노랑": ["황색", "연황", "레몬색"],
            "주황": ["주황", "단주황"],
            "분홍": ["분홍", "연분홍", "담분홍"],
            "빨강": ["적색", "담적색", "진적색"],
            "갈색": ["갈색", "연갈", "황갈", "다갈"],
            "연두": ["연두"],
            "초록": ["녹색", "연녹", "진녹"],
            "청록": ["청록"],
            "파랑": ["청색", "연란", "소라", "물색"],
            "남색": ["남색", "진청"],
            "보라": ["보라", "자색"],
            "회색": ["회색"],
            "검정": ["검정"],
        }

        # 2. OCR 유사 문자 그룹
        self.OCR_GROUPS = [{"T", "I", "1", "L"}, {"Q", "O", "D", "0"}, {"5", "S"}, {"8", "B"}]

    def _get_expanded_imprints(self, text):
        """OCR 오차 및 구분자(콤마, 공백) 처리 포함 확장"""
        if not text:
            return []

        # 1. 콤마나 공백 제거 및 정규화
        raw_text = text.upper().replace(",", "").replace(" ", "")
        chars = list(raw_text)
        results = {raw_text}  # 세트로 중복 방지

        # 2. 유사 문자 그룹 확장
        for i, char in enumerate(chars):
            for group in self.OCR_GROUPS:
                if char in group:
                    for replacement in group:
                        new_text_list = chars.copy()
                        new_text_list[i] = replacement
                        results.add("".join(new_text_list))

        # 3. (추가) 원본 텍스트에 콤마가 포함된 경우 각각의 조각도 후보에 추가
        if "," in text:
            parts = text.upper().split(",")
            for p in parts:
                results.add(p.strip())

        return list(results)

    # ==================================================
    # File Operations
    # ==================================================

    async def file_save(self, user: Any, files: list[UploadFile]):
        upload_dir = self.UPLOAD_DIR
        Path(upload_dir).mkdir(parents=True, exist_ok=True)
        uploaded_db_params = []

        for i, file in enumerate(files):
            suffix = "_front" if i == 0 else "_back"
            category = "pill_front" if i == 0 else "pill_back"

            filename = file.filename or "unknown"
            ext = Path(filename).suffix
            clean_name = Path(filename).stem.replace(" ", "_")
            unique_filename = f"{uuid.uuid4().hex}_{clean_name}{suffix}{ext}"
            file_path = os.path.join(upload_dir, unique_filename)

            async with await anyio.open_file(file_path, "wb") as f:
                while chunk := await file.read(1024 * 1024):
                    await f.write(chunk)

            uploaded_db_params.append(
                {
                    "file_path": file_path,
                    "original_name": filename,
                    "file_type": file.content_type,
                    "category": category,
                }
            )

        created_uploads = await self._repo.create_file(user.id, uploaded_db_params)
        return await self.pill_name_result(created_uploads)

    # ==================================================
    # Identification Logic
    # ==================================================

    async def pill_name_result(self, uploaded_results):
        # 1. 이미지 Base64 인코딩
        base64_imgs = {}
        for row in uploaded_results:
            with open(row.file_path, "rb") as f:
                base64_imgs[row.category] = base64.b64encode(f.read()).decode("utf-8")

        # 2. Vision 분석 요청 (필드 4개로 고정)
        prompt = """
        의약품 식별 전문가로서 이미지를 분석하여 알약의 특징을 추출해줘.
        반드시 아래의 **JSON** 구조로만 답변해야 해.

        [출력 규칙]
        1. text: image1, image2의 OCR 문자(영어, 숫자 조합). 없으면 빈 문자열.
        2. text: 문자가 위/아래 또는 좌/우로 나뉘어 있으면 ','로 구분 (예: 'SK,T')
        4. text: {'T', 'I', '1', 'L'},
            {'Q', 'O', 'D', '0'},
            {'5', 'S'},
            {'8', 'B'} 이렇게 그룹화 된 부분의 인식이 어려울 거라 특히 확실히 체크해줘 각각 특징을 보고
        3. color: [하양,노랑,주황,분홍,빨강,갈색,연두,초록,청록,파랑,남색,자주,보라,회색,검정,투명] 중 선택
        4. formulation: [정제,경질캡슐,연질캡슐,기타] 중 선택
           - 투명하고 액체가 들어있으면 '연질캡슐', 조립된 형태면 '경질캡슐'.
        5. shape: [원형,타원형,장방형,반원형,삼각형,사각형,마름모형,오각형,육각형,팔각형,기타] 중 선택

        {{
            "image1" : {{
                "text" : "",
                "color": "",
                "formulation": "",
                "shape": ""
            }},
            "image2" : {{
                "text" : "",
                "color": "",
                "formulation": "",
                "shape": ""
            }}
        }}
        """

        ai_analysis = await self.llm_service.generate_json(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_imgs.get('pill_front')}"},
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_imgs.get('pill_back')}"},
                        },
                    ],
                }
            ],
            model=self.VISION_MODEL,
            temperature=0.1,
        )

        ai_feat = ai_analysis.get("content", ai_analysis) if isinstance(ai_analysis, dict) else ai_analysis

        img1 = ai_feat.get("image1", {})
        img2 = ai_feat.get("image2", {})

        # --- [1] 각인(text) 처리 ---
        t1 = (img1.get("text") or "").strip().upper()
        t2 = (img2.get("text") or "").strip().upper()

        # OCR 오차 보정 포함 후보 생성
        cands1 = self._get_expanded_imprints(t1)
        cands2 = self._get_expanded_imprints(t2)
        combined_cands = self._get_expanded_imprints(t1 + t2) + self._get_expanded_imprints(t2 + t1)
        all_imprints = list(set(cands1 + cands2 + combined_cands))

        # --- [2] 색상(color) 처리 ---
        ai_color = img1.get("color", "하양")
        search_colors = self.COLOR_GROUPS.get(ai_color, [ai_color])

        # --- [3] 모양(shape) 처리 ---
        ai_shape = img1.get("shape", "")
        standard_shapes = ["원형", "타원형", "장방형"]
        if ai_shape in standard_shapes:
            shape_condition = self.db_df["성상"].str.contains(ai_shape, na=False)
        else:
            shape_condition = ~self.db_df["성상"].str.contains("|".join(standard_shapes), na=False)

        # --- [4] 제형(formulation) 처리 ---
        ai_form = img1.get("formulation", "")
        if "경질" in ai_form:
            form_condition = self.db_df["제형코드명"].str.contains("경질캡슐", na=False)
        elif "연질" in ai_form:
            form_condition = self.db_df["제형코드명"].str.contains("연질캡슐", na=False)
        elif "정제" in ai_form:
            form_condition = self.db_df["제형코드명"].str.contains("정제", na=False)
        else:
            form_condition = True

        # --- [5] 필터링 ---
        df = self.db_df.copy()
        imprint_mask = (
            df["표시앞"].isin(all_imprints)
            | df["표시뒤"].isin(all_imprints)
            | (df["표시앞"] + df["표시뒤"]).isin(all_imprints)
        )

        # 1차 필터 (각인 & 모양 & 제형)
        candidates = df[imprint_mask & shape_condition & form_condition].copy()

        # 결과 부족 시 각인만으로 확장
        if len(candidates) == 0:
            candidates = df[imprint_mask].copy()

        # --- [6] 스코어링 및 TOP 3 추출 ---
        final_list = []
        for _, row in candidates.iterrows():
            score = 0.5  # 각인 통과 기본점수

            # 색상 일치 가점 (+0.3)
            db_color = str(row["색상앞"]) + str(row["색상뒤"])
            if any(c in db_color for c in search_colors):
                score += 0.3

            # 제형 정확도 가점 (+0.2)
            if ai_form[:2] in str(row["제형코드명"]):
                score += 0.2

            final_list.append(
                {
                    "name": row["품목명"],
                    "company": row["업소명"],
                    "score": round(score, 2),
                    "image_path": row["큰제품이미지"],
                    "reason": "분석 결과 가장 일치하는 의약품",
                }
            )

        # 점수순 정렬 후 상위 3개만 반환
        final_list = sorted(final_list, key=lambda x: x["score"], reverse=True)[:3]

        return {"status": "success", "ai_extracted": ai_feat, "candidates": final_list}

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

    async def get_upload_history(self, user: Any) -> list[dict]:
        """
        사용자의 전체 업로드 히스토리를 가져와 프론트엔드 표시에 맞게 가공합니다.
        가공 형태: 여러 장의 사진이 같은 날짜에 올라가더라도 날짜와 카테고리를 기준으로 하나로 묶습니다.
        """
        if not user:
            return []

        uploads = await self._repo.get_all_uploads(user.id)
        if not uploads:
            return []

        history_map = {}
        for upload in uploads:
            # 날짜 (YYYY-MM-DD 형식으로만)
            created_date = upload.created_at.strftime("%Y-%m-%d")

            # 카테고리 (UI 표시용)
            if upload.category == "prescription":
                display_type = "처방전"
            elif upload.category in ["pill_front", "pill_back"]:
                display_type = "알약 분석"
            else:
                display_type = upload.category

            # 이미지 파일 URL 계산 (FastAPI StaticFiles 경로 기준)
            file_name_only = os.path.basename(upload.file_path)
            file_url = f"/uploads/{file_name_only}"
            original_name = upload.original_name or file_name_only

            # 같은 날짜 + 같은 타입인 경우 한 항목으로 보여줌
            key = f"{created_date}_{display_type}"
            if key not in history_map:
                history_map[key] = {"id": upload.id, "date": created_date, "type": display_type, "images": []}

            history_map[key]["images"].append({"name": original_name, "url": file_url})

        # 딕셔너리의 값만 리스트로 반환 (최근순 정렬 유지)
        return list(history_map.values())

    async def delete_upload_file(self, user: Any, upload_id: int) -> bool:
        """
        특정 업로드 레코드를 삭제합니다.
        사용자 소유 파일만 삭제할 수 있으며, 성공 시 True를 반환합니다.
        """
        if not user:
            return False
        # await 결과를 bool()로 감싸서 명시적으로 타입을 맞춰줍니다.
        result = await self._repo.delete_upload(upload_id, user.id)
        return bool(result)

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
            front_asset = getattr(front, "pill_recognition_front", None) if front else None
            back_asset = getattr(back, "pill_recognition_back", None) if back else None
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
