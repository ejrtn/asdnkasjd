import io
import json
import time
import uuid
from typing import TYPE_CHECKING, Any

from app.models.user import User
from app.utils.ocr_processing import preprocess_image_for_ocr

if TYPE_CHECKING:
    from pypdf import PdfReader
else:
    try:
        from pypdf import PdfReader
    except ImportError:
        PdfReader = None  # type: ignore

from fastapi import HTTPException, status

from app.core import config
from app.core.http_client import http_client
from app.core.logger import default_logger
from app.dtos.ocr import DrugInfo, OCRExtractResponse, PillAnalyzeResponse, PillCandidate
from app.repositories.prescription import PrescriptionRepository


class OCRService:
    def __init__(self):
        self.prescription_repo = PrescriptionRepository()

    async def extract_raw_text(self, image_bytes: bytes, file_name: str, file_ext: str) -> str:
        """
        PDF인 경우 우선 텍스트 추출을 시도하고, 실패하거나 이미지 기반 PDF인 경우 Naver Clova OCR을 사용합니다.
        """
        # 1. PDF 텍스트 직접 추출 시도
        if file_ext.lower() == ".pdf":
            native_text = self._extract_native_pdf_text(image_bytes, file_name)
            if native_text:
                return native_text

        # 2. Naver Clova OCR 사용 (이미지 또는 텍스트 없는 PDF)
        return await self._extract_clova_ocr_text(image_bytes, file_name, file_ext)

    def _extract_native_pdf_text(self, image_bytes: bytes, file_name: str) -> str | None:
        """PDF에서 직접 텍스트를 추출합니다."""
        try:
            if PdfReader is None:
                return None
            reader = PdfReader(io.BytesIO(image_bytes))
            native_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    native_text += text + "\n"

            # 추출된 텍스트가 의미 있는 수준(50자 이상)이면 반환
            if len(native_text.strip()) > 50:
                return native_text.strip()
        except Exception as e:
            default_logger.error(f"Native PDF extraction failed for {file_name}: {e}")
        return None

    async def _extract_clova_ocr_text(self, image_bytes: bytes, file_name: str, file_ext: str) -> str:
        """Naver Clova OCR API를 사용하여 텍스트를 추출합니다. 전처리를 포함합니다."""
        invoke_url = config.CLOVA_OCR_INVOKE_URL
        secret_key = config.CLOVA_OCR_SECRET_KEY

        if not invoke_url or not secret_key:
            default_logger.error("Naver Clova OCR configuration is missing (URL or Secret Key).")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="OCR 서비스 설정이 누락되었습니다."
            )

        # 이미지 전처리 시행 (OpenCV Utility 사용)
        processed_bytes = preprocess_image_for_ocr(image_bytes)

        request_json = {
            "images": [{"format": file_ext.replace(".", ""), "name": file_name}],
            "requestId": str(uuid.uuid4()),
            "version": "V2",
            "timestamp": int(time.time() * 1000),
        }

        headers = {"X-OCR-SECRET": secret_key}
        payload = {"message": json.dumps(request_json)}
        files = {"file": (file_name, processed_bytes)}

        try:
            client = http_client.client
            response = await client.post(invoke_url, headers=headers, data=payload, files=files, timeout=30.0)

            if response.status_code != 200:
                default_logger.error(f"Naver Clova OCR API failed with status {response.status_code}: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY, detail=f"OCR API 호출 실패: {response.status_code}"
                )

            res_data = response.json()
            all_text = []
            for image in res_data.get("images", []):
                for field in image.get("fields", []):
                    all_text.append(field.get("inferText", ""))
                    all_text.append(" ")
            return "".join(all_text).strip()
        except HTTPException:
            raise
        except Exception as e:
            default_logger.exception(f"Unexpected error during OCR processing for {file_name}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"OCR 처리 중 오류 발생: {str(e)}"
            ) from e

    # ==========================================
    # [추가된 기능] 필수 3: OCR 기반 의료정보 인식
    # ==========================================
    async def extract_text_from_image(self, image_bytes: bytes) -> OCRExtractResponse:
        """
        처방전 및 진료비 계산서 이미지에서 의료 텍스트를 추출하고 정규화합니다.
        병원명, 처방일자, 개별 약품명 및 복약 정보를 구조화하여 반환합니다.

        Args:
            image_bytes (bytes): 분석할 이미지 또는 PDF 바이너리 데이터

        Returns:
            OCRExtractResponse: 정규화된 의료 정보 및 추출된 약품 상세 리스트
        """
        # 1. 이미지/PDF에서 텍스트 자동 추출 (더미 로직)
        # 2. 정규화 처리 (mg/ml, YYYY-MM-DD)
        dummy_drugs = [
            DrugInfo(drug_name="타이레놀정500mg", dosage="500mg", frequency="1일 3회", duration="3"),
            DrugInfo(drug_name="아모디핀정", dosage="5mg", frequency="1일 1회", duration="30"),
        ]
        return OCRExtractResponse(
            hospital_name="서울대학교병원",
            prescribed_date="2024-02-24",
            drugs=dummy_drugs,
            extracted_text="[처방전] 서울대학교병원 ... 타이레놀정 500밀리그램 ...",
            confidence=0.98,
            multimodal_assets=[],
        )

    # ==========================================
    # [추가된 기능] 선택 2: 이미지 분류 기반 복약 분석 (CNN)
    # ==========================================
    async def analyze_pill_image(self, image_bytes: bytes) -> PillAnalyzeResponse:
        """
        단일 약품 이미지를 분석하여 CNN 모델 기반으로 약품명을 식별합니다. (기존 더미 유지 필수 시)
        """
        # (기존 더미 로직 생략 또는 유지)
        candidates = [
            PillCandidate(pill_name="타이레놀정500mg", confidence=0.85, medication_info="진통제"),
            PillCandidate(pill_name="에어탈정", confidence=0.10, medication_info="소염제"),
            PillCandidate(pill_name="노바스크정", confidence=0.03, medication_info="혈압약"),
        ]
        top = candidates[0]
        return PillAnalyzeResponse(candidates=candidates, top_candidate=top, multimodal_assets=[], suggestion=None)

    async def identify_pill_with_llm(self, front_image: bytes, back_image: bytes | None = None) -> dict[str, Any]:
        """
        GPT-4o-mini Vision을 사용하여 알약의 이미지를 분석하여 특성을 추출하고,
        MFDS API를 통해 실제 의약품 후보군을 검색합니다.
        """
        import base64

        from openai.types.chat import ChatCompletionUserMessageParam

        from app.services.mfds_service import MFDSService

        mfds_service = MFDSService()

        front_b64 = base64.b64encode(front_image).decode("utf-8")
        contents: list[ChatCompletionUserMessageParam] = [
            {"type": "text", "text": "이 알약 이미지를 분석해서 검색을 위한 특징을 추출해줘."},  # type: ignore[typeddict-item]
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{front_b64}"},
            },  # type: ignore[typeddict-item]
        ]

        if back_image:
            back_b64 = base64.b64encode(back_image).decode("utf-8")
            contents.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{back_b64}"},
                }  # type: ignore[typeddict-item]
            )

        prompt = """
        알약의 사진을 보고 검색 필터링을 위한 정보를 JSON 형식으로 추출해세요:
        1. name: 알약의 이름 (추정되는 제품명)
        2. marking_front: 알약 앞면의 각인 (글자, 숫자, 기호 등)
        3. marking_back: 알약 뒷면의 각인 (글자, 숫자, 기호 등)
        4. color: 색상 (하양, 노랑, 주황, 분홍, 빨강, 갈색, 연두, 초록, 청록, 파랑, 보라, 회색, 검정, 투명 중 선택)
        5. shape: 모양 (원형, 타원형, 반원형, 삼각형, 사각형, 오각형, 육각형, 팔각형, 마름모형, 기타 중 선택)
        6. display_text: 사용자에게 보여줄 간단한 외형 묘사 (예: 노란색의 타원형 정제, 앞면 각인 AT)

        반드시 지정된 옵션 내에서 선택하고 JSON 형식만 출력하세요.
        """
        contents[0]["text"] = prompt  # type: ignore[typeddict-item]

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

            response = await client.chat.completions.create(  # type: ignore[call-overload]
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": contents}],
                response_format={"type": "json_object"},
                temperature=0,
            )

            traits = json.loads(response.choices[0].message.content or "{}")
            default_logger.info(f"[LLM Vision] Extracted Traits for MFDS Search: {traits}")

            # 2. MFDS API 검색 수행
            candidates = await mfds_service.get_identified_candidates(traits)
            default_logger.info(f"[MFDS API] Found {len(candidates)} candidates.")

            # 3. 최종 결과 구성
            top_candidate = candidates[0] if candidates else None

            return {
                "name": top_candidate.pill_name if top_candidate else traits.get("name", "식별 실패"),
                "efficacy": top_candidate.medication_info if top_candidate else "N/A",
                "appearance": {
                    "marking": f"{traits.get('marking_front', '')}/{traits.get('marking_back', '')}",
                    "color": traits.get("color"),
                    "shape": traits.get("shape"),
                },
                "candidates": [c.dict() for c in candidates],
                "confidence": top_candidate.confidence if top_candidate else 0.0,
                "display_text": traits.get("display_text", "분석 완료"),
                "caution": "식약처 정보를 바탕으로 검색된 결과입니다.",
            }
        except Exception as e:
            default_logger.error(f"Pill Identification Error: {str(e)}")
            return {
                "name": "식별 실패",
                "efficacy": "N/A",
                "appearance": {"marking": "N/A", "color": "N/A", "shape": "N/A"},
                "candidates": [],
                "confidence": 0.0,
                "display_text": f"오류 발생: {str(e)}",
                "caution": "분석 중 오류가 발생했습니다.",
            }

    async def last_prescription(self, user: User):
        result = await self.prescription_repo.last_prescription(user)
        return result or []
