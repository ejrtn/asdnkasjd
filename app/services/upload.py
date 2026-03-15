import base64
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any

import anyio
from fastapi import UploadFile
from tortoise.expressions import Q

from app.models.drug_master import DrugMaster
from app.repositories.upload import UploadRepository
from app.services.drug_enrichment_service import DrugEnrichmentService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class UploadService:
    UPLOAD_DIR = "/app/uploads/"
    CHROMA_DB_PATH = "./data/chroma_db"
    VISION_MODEL = "gpt-4o-mini"
    COLLECTION_NAME = "pill_database"

    def __init__(self):
        self._repo = UploadRepository()
        self.llm_service = LLMService()

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

        # 2. Vision 분석 요청
        ai_feat = await self._get_ai_analysis(base64_imgs)
        img1 = ai_feat.get("image1", {})
        img2 = ai_feat.get("image2", {})

        # 3. AI 추출 데이터 정리 및 후보군 생성
        t1_raw = (img1.get("text") or "").strip().upper()
        t2_raw = (img2.get("text") or "").strip().upper()
        cands1 = self._get_expanded_imprints(t1_raw)
        cands2 = self._get_expanded_imprints(t2_raw)

        # 4. DB 1차 필터링
        candidates = await self._get_db_candidates(img1)

        # 5. 스코어링 및 필터링
        final_list = self._score_candidates(candidates, img1, img2, cands1, cands2)

        # 6. 상위 3개 추출 및 정보 보충
        final_list = sorted(final_list, key=lambda x: x["score"], reverse=True)[:3]

        if not final_list:
            return {
                "status": "success",
                "ai_extracted": ai_feat,
                "candidates": [],
                "message": "일치하는 약이 없습니다.",
            }

        await self._enrich_missing_info(final_list)

        return {"status": "success", "ai_extracted": ai_feat, "candidates": final_list}

    async def _get_ai_analysis(self, base64_imgs):
        """Vision 분석 요청 및 결과 반환"""
        prompt = """
        의약품 식별 전문가로서 이미지를 분석하여 알약의 특징을 추출해줘.
        반드시 아래의 **JSON** 구조로만 답변해야 해.

        [출력 규칙]
        1. text: image1, image2의 OCR 문자(영어, 숫자 조합). 없으면 빈 문자열.
        2. text: 문자가 위/아래 또는 좌/우로 나뉘어 있으면 ','로 구분 (예: 'SK,T')
        3. color: [하양,노랑,주황,분홍,빨강,갈색,연두,초록,청록,파랑,남색,자주,보라,회색,검정,투명] 중 선택
        4. formulation: [정제,경질캡슐,연질캡슐,기타] 중 선택
           - 투명하고 액체가 들어있으면 '연질캡슐', 조립된 형태면 '경질캡슐'.
        5. shape: [원형,타원형,장방형,반원형,삼각형,사각형,마름모형,오각형,육각형,팔각형,기타] 중 선택

        {
            "image1" : {
                "text" : "",
                "color": "",
                "formulation": "",
                "shape": ""
            },
            "image2" : {
                "text" : "",
                "color": "",
                "formulation": "",
                "shape": ""
            }
        }
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
        return ai_analysis.get("content", ai_analysis) if isinstance(ai_analysis, dict) else ai_analysis

    async def _get_db_candidates(self, img1):
        """기본 정보를 기반으로 DB에서 후보군 조회"""

        ai_shape = img1.get("shape", "")
        ai_form = img1.get("formulation", "")

        query = Q()
        if ai_shape:
            query |= Q(drug_shape__icontains=ai_shape)
        if ai_form:
            query |= Q(form_code_name__icontains=ai_form[:2])

        return await DrugMaster.filter(query).all()

    def _score_candidates(self, candidates, img1, img2, cands1, cands2):
        """후보군들에 대해 AI 분석값과 비교하여 스코어링"""
        final_list = []
        ai_shape = img1.get("shape", "")
        ai_form = img1.get("formulation", "")

        for row in candidates:
            db_f_text = (row.print_front or "").strip().upper()
            db_b_text = (row.print_back or "").strip().upper()
            db_shape = row.drug_shape or ""
            db_form = row.form_code_name or ""

            # 색상 그룹화
            ai_color1 = img1.get("color", "")
            ai_color2 = img2.get("color", "")
            search_colors1 = self.COLOR_GROUPS.get(ai_color1, [ai_color1])
            search_colors2 = self.COLOR_GROUPS.get(ai_color2, [ai_color2])

            # 시나리오 A & B 계산
            score_a = self._calculate_match(
                db_f_text, db_b_text, row.color_class1, row.color_class2, cands1, cands2, search_colors1, search_colors2
            )
            score_b = self._calculate_match(
                db_f_text, db_b_text, row.color_class1, row.color_class2, cands2, cands1, search_colors2, search_colors1
            )

            # 공통 항목
            common_score = 0
            if ai_shape and ai_shape in db_shape:
                common_score += 0.2
            if ai_form and ai_form[:2] in db_form:
                common_score += 0.2

            total_score = round(max(score_a, score_b) + common_score, 2)

            if total_score > 0.3:
                final_list.append(
                    {
                        "drug_id": row.item_seq,
                        "name": row.item_name,
                        "company": row.entp_name,
                        "score": total_score,
                        "image_path": row.item_image,
                        "reason": f"일치도 {int(total_score * 100)}% 분석 결과",
                        "efcy_qesitm": row.efcy_qesitm,
                        "use_method_qesitm": row.use_method_qesitm,
                        "atpn_warn_qesitm": row.atpn_warn_qesitm,
                        "atpn_qesitm": row.atpn_qesitm,
                        "intrc_qesitm": row.intrc_qesitm,
                        "se_qesitm": row.se_qesitm,
                        "deposit_method_qesitm": row.deposit_method_qesitm,
                        "source": row.source,
                    }
                )
        return final_list

    def _calculate_match(
        self, db_f_text, db_b_text, db_f_color, db_b_color, cands_f, cands_b, search_colors_f, search_colors_b
    ):
        """특정 방향 매칭 스코어 계산"""
        score = 0
        if db_f_text and db_f_text in cands_f:
            score += 0.2
        if db_b_text and db_b_text in cands_b:
            score += 0.2
        if any(c in (db_f_color or "") for c in search_colors_f):
            score += 0.1
        if any(c in (db_b_color or "") for c in search_colors_b):
            score += 0.1
        return score

    async def _enrich_missing_info(self, final_list):
        """부족한 약물 정보를 LLM으로 실시간 보충"""

        enricher = DrugEnrichmentService()

        for item in final_list:
            if not item.get("efcy_qesitm"):
                drug_record = await DrugMaster.filter(item_seq=item["drug_id"]).first()
                if drug_record:
                    enriched_data = await enricher._generate_drug_info(drug_record)
                    if enriched_data:
                        update_dict = enriched_data.model_dump()
                        update_dict["source"] = "AI"
                        await drug_record.update_from_dict(update_dict).save()
                        for key, value in update_dict.items():
                            item[key] = value

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
