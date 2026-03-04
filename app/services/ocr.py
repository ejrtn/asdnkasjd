import io
import json
import time
import uuid
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from pypdf import PdfReader
else:
    try:
        from pypdf import PdfReader
    except ImportError:
        PdfReader = None  # type: ignore

from app.core import config
from app.dtos.ocr import DrugInfo, OCRExtractResponse, PillAnalyzeResponse, PillCandidate


class OCRService:
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
            print(f"Native PDF extraction failed for {file_name}: {e}")
        return None

    async def _extract_clova_ocr_text(self, image_bytes: bytes, file_name: str, file_ext: str) -> str:
        """Naver Clova OCR API를 사용하여 텍스트를 추출합니다."""
        invoke_url = config.CLOVA_OCR_INVOKE_URL
        secret_key = config.CLOVA_OCR_SECRET_KEY

        if not invoke_url or not secret_key:
            return "Naver Clova OCR 설정이 누락되었습니다."

        request_json = {
            "images": [{"format": file_ext.replace(".", ""), "name": file_name}],
            "requestId": str(uuid.uuid4()),
            "version": "V2",
            "timestamp": int(time.time() * 1000),
        }

        headers = {"X-OCR-SECRET": secret_key}
        payload = {"message": json.dumps(request_json)}
        files = {"file": (file_name, image_bytes)}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(invoke_url, headers=headers, data=payload, files=files, timeout=30.0)
                if response.status_code != 200:
                    return f"OCR API 오류: {response.text}"

                res_data = response.json()
                all_text = []
                for image in res_data.get("images", []):
                    for field in image.get("fields", []):
                        all_text.append(field.get("inferText", ""))
                        all_text.append(" ")
                return "".join(all_text).strip()
        except Exception as e:
            return f"OCR 요청 중 예외 발생: {str(e)}"

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
        단일 약품 이미지를 분석하여 CNN 모델 기반으로 약품명을 식별합니다.
        식별 신뢰도가 낮을 경우 재촬영 안내 메시지를 포함합니다.

        Args:
            image_bytes (bytes): 분석할 약품 사진 바이너리 데이터

        Returns:
            PillAnalyzeResponse: 식별된 후보군 리스트와 최적 후보 정보
        """
        # 1. CNN Transfer Learning 모델 기반 인식 (더미)
        # 2. 상위 3개 후보 추출 및 신뢰도 판단
        candidates = [
            PillCandidate(pill_name="타이레놀정500mg", confidence=0.85, medication_info="진통제"),
            PillCandidate(pill_name="에어탈정", confidence=0.10, medication_info="소염제"),
            PillCandidate(pill_name="노바스크정", confidence=0.03, medication_info="혈압약"),
        ]

        top = candidates[0]
        suggestion = None
        if top.confidence < 0.60:
            suggestion = "약품 인식 신뢰도가 낮습니다. 직접 입력하시거나 다시 촬영해 주세요."

        return PillAnalyzeResponse(
            candidates=candidates, top_candidate=top, suggestion=suggestion, multimodal_assets=[]
        )
