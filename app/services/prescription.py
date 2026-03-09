import json
import logging
from datetime import date
from typing import Any

from openai import AsyncOpenAI

from app.core import config
from app.models.upload import Upload
from app.models.user import User
from app.repositories.prescription import PrescriptionRepository

logger = logging.getLogger(__name__)


class PrescriptionService:
    """
    LLM을 사용하여 처방전의 OCR 텍스트를 파싱하고 정제된 데이터를 관리하는 서비스 클래스입니다.
    """

    def __init__(self):
        self.repo = PrescriptionRepository()
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

    async def parse_prescription_with_llm(self, raw_text: str) -> dict[str, Any]:
        """
        OpenAI LLM을 사용하여 OCR 텍스트에서 병원명, 처방일자, 약물 리스트를 추출합니다 (Step 3 & 4).
        """
        if not config.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY가 설정되지 않았습니다. 파싱을 건너뜁니다.")
            return {"hospital_name": None, "prescribed_date": None, "drugs": []}

        system_prompt = """
        당신은 처방전 분석 전문가입니다. 주어진 OCR 텍스트에서 '병원 이름', '발행 일자', 그리고 '처방된 약물 리스트'를 추출하세요.
        [JSON 구조 규칙]
        {
            "hospital_name": "병원명 또는 null",
            "prescribed_date": "YYYY-MM-DD 또는 null",
            "drug_list_raw": "추출된 약물 이름들을 쉼표로 구분한 문자열 (예: 타이레놀, 아스피린)",
            "drugs": [
                {
                    "name": "표준 약물명",
                    "dosage": 1.0, (1회 투여량, 숫자)
                    "frequency": 3, (하루 복용 횟수, 정수)
                    "duration": 7 (총 복용 일수, 정수)
                }
            ]
        }
        날짜는 반드시 YYYY-MM-DD 형식으로 변환하고, 숫자는 가능한 경우 정수나 실수로 추출하세요.
        """

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"OCR 텍스트: {raw_text}"},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )

            result = json.loads(response.choices[0].message.content or "{}")
            logger.info(f"LLM Prescription Parsing Result: {result}")
            return result  # type: ignore[no-any-return]
        except Exception as e:
            logger.error(f"LLM 파싱 오류: {str(e)}")
            return {"hospital_name": None, "prescribed_date": None, "drug_list_raw": None, "drugs": []}

    async def process_prescription_parsing(self, user: User, upload: Upload, raw_text: str) -> Any:
        """
        OCR 텍스트를 파싱하여 Prescription 레코드(Step 3)를 먼저 생성한 후,
        개별 PrescriptionDrug 레코드(Step 5)를 생성합니다.
        """
        # 1. LLM 파싱 실행
        parsed_data = await self.parse_prescription_with_llm(raw_text)

        hospital_name = parsed_data.get("hospital_name")
        prescribed_date_str = parsed_data.get("prescribed_date")
        drug_list_raw = parsed_data.get("drug_list_raw")
        drugs_data = parsed_data.get("drugs", [])

        # 2. 날짜 형식 검증 및 변환
        prescribed_date = None
        if prescribed_date_str:
            try:
                prescribed_date = date.fromisoformat(prescribed_date_str)
            except ValueError:
                logger.warning(f"잘못된 날짜 형식: {prescribed_date_str}")

        # 3. Step 3: Prescription 테이블 저장 (병원명, 날짜, 약물 원본 리스트)
        prescription = await self.repo.create(
            user=user,
            upload=upload,
            hospital_name=hospital_name,
            prescribed_date=prescribed_date,
            drug_list_raw=drug_list_raw,
        )

        # 4. Step 5: PrescriptionDrug 테이블 저장 (개별 약물 상세 정보)
        for drug in drugs_data:
            try:
                await self.repo.create_drug(
                    prescription=prescription,
                    standard_drug_name=drug.get("name"),
                    dosage_amount=drug.get("dosage"),
                    daily_frequency=drug.get("frequency"),
                    duration_days=drug.get("duration"),
                )
            except Exception as e:
                logger.error(f"약물 데이터 저장 실패: {drug.get('name')}, 에러: {str(e)}")

        return prescription
