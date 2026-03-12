import json
import logging
from datetime import date
from typing import Any

from openai import AsyncOpenAI

from app.core import config
from app.models.ocr_history import OCRHistory
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

    async def parse_prescription_with_vision(self, image_bytes: bytes) -> dict[str, Any]:
        """
        GPT-4o-mini Vision을 사용하여 처방전 이미지를 직접 분석하고 구조화된 데이터를 추출합니다.
        회전되거나 뒤집힌 이미지도 자동으로 처리하며, 노이즈를 효과적으로 필터링합니다.
        """
        import base64

        if not config.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY가 설정되지 않았습니다. 파싱을 건너뜁니다.")
            return {"hospital_name": None, "prescribed_date": None, "drugs": []}

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        system_prompt = """
        당신은 한국의 처방전 및 약봉투 분석 전문가입니다. 이미지를 보고 '병원/약국명', '날짜', '약물 정보'를 JSON으로 추출하세요.

        ### [핵심 분석 규칙 - 매우 중요] ###
        1. **컬럼 구분**:
           - '약품명' 컬럼과 '복약안내' 컬럼을 엄격히 구분하세요.
           - '약품명' 컬럼에 적힌 고유 이름(예: 셋락타민정, 나로펜정)만 'name' 필드에 담으세요.
           - '복약안내' 컬럼에 적힌 설명(예: ~치료하는 약, ~해소하는 약)은 절대로 'name' 필드에 넣지 마세요.
        2. **텍스트 정제**:
           - 약품명 뒤의 특수문자(_), 괄호 안의 용량((0.5g)), 또는 잘린 텍스트 부분을 정제하여 깔끔한 제품명만 남기세요.
        3. **불필요 정보 제외**:
           - 조제약사명, 환자명, 영수증 금액 등 약품 리스트가 아닌 정보는 모두 무시하세요.
        4. **개수 확인**:
           - 표의 행(Row) 개수만큼 약물이 추출되어야 합니다. (예: 3줄이면 3개 추출)
        5. **방향 무관**:
           - 사진이 거꾸로 되어 있어도 글자 방향을 읽어 정확히 파악하세요.

        ### JSON 구조 ###
        {
            "hospital_name": "병원명 또는 약국명 (null 가능)",
            "prescribed_date": "YYYY-MM-DD (null 가능)",
            "drug_list_raw": "추출된 약물 이름들 (쉼표 구분)",
            "drugs": [
                {
                    "name": "정제된 표준 약품명",
                    "dosage": 1.0, (1회 분량)
                    "frequency": 3, (하루 횟수)
                    "duration": 3 (복용 일수)
                }
            ]
        }
        """

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "이 처방전/약봉투 이미지를 분석해줘."},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                            },
                        ],
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )

            result = json.loads(response.choices[0].message.content or "{}")
            logger.info(f"Vision Prescription Parsing Result: {result}")
            return result  # type: ignore[no-any-return]
        except Exception as e:
            logger.error(f"Vision 파싱 오류: {str(e)}")
            return {"hospital_name": None, "prescribed_date": None, "drug_list_raw": None, "drugs": []}

    async def process_prescription_vision_parsing(self, user: User, upload: Upload, image_bytes: bytes) -> Any:
        """
        Vision 파싱을 실행하고 결과를 DB에 저장합니다.
        """
        # 1. Vision 파싱 실행
        parsed_data = await self.parse_prescription_with_vision(image_bytes)

        hospital_name = parsed_data.get("hospital_name")
        prescribed_date_str = parsed_data.get("prescribed_date")
        drug_list_raw = parsed_data.get("drug_list_raw")
        drugs_data = parsed_data.get("drugs", [])

        # 2. 날짜 형식 검증
        prescribed_date = None
        if prescribed_date_str:
            try:
                prescribed_date = date.fromisoformat(prescribed_date_str)
            except ValueError:
                logger.warning(f"잘못된 날짜 형식: {prescribed_date_str}")

        # 3. OCRHistory 생성 (Vision 분석 원본 결과 저장)
        ocr_history = await OCRHistory.create(
            user=user,
            raw_text=json.dumps(parsed_data, ensure_ascii=False),
            is_valid=True,
            front_upload=upload,
            inference_metadata={"model": "gpt-4o-mini-vision"},
        )

        # 4. Prescription 생성
        prescription = await self.repo.create(
            user=user,
            upload=upload,
            ocr_history=ocr_history,
            hospital_name=hospital_name,
            prescribed_date=prescribed_date,
            drug_list_raw=drug_list_raw,
        )

        # 4. PrescriptionDrug 생성
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

    async def parse_prescription_with_llm(self, raw_text: str) -> dict[str, Any]:
        """
        (Deprecated) OpenAI LLM을 사용하여 OCR 텍스트에서 데이터를 추출합니다.
        이제 parse_prescription_with_vision 사용을 권장합니다.
        """
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
        if not drugs_data and drug_list_raw:
            # drugs_data가 비어있다면 drug_list_raw를 파싱해서 최소한의 약물 정보라도 저장
            raw_drugs = [name.strip() for name in drug_list_raw.split(",") if name.strip()]
            for name in raw_drugs:
                try:
                    await self.repo.create_drug(
                        prescription=prescription,
                        standard_drug_name=name,
                        dosage_amount=None,
                        daily_frequency=None,
                        duration_days=None,
                    )
                except Exception as e:
                    logger.error(f"약물 데이터(raw) 저장 실패: {name}, 에러: {str(e)}")
        else:
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

    async def sync_to_current_meds(
        self, prescription_id: int, user: User, drug_names: list[str] | None = None
    ) -> list[Any]:
        """
        [Step 6] 처방전의 약물들을 현재 복용 중인 약물(CurrentMed) 테이블로 복사(연동)합니다.
        drug_names가 제공될 경우 해당 약물들만 선택하여 연동합니다.
        """
        from app.models.current_med import AddedFrom, CurrentMed, DoseTime

        prescription = await self.repo.get_by_id(prescription_id)
        if not prescription or prescription.user_id != user.id:
            raise ValueError("처방전을 찾을 수 없거나 권한이 없습니다.")

        drugs = await prescription.drugs.all()
        created_meds = []

        for drug in drugs:
            # 선택된 약물 리스트가 있다면 필터링
            if drug_names is not None and drug.standard_drug_name not in drug_names:
                continue

            # 기본적으로 아침 복용으로 설정 (사용자가 나중에 수정 가능하도록 가이드)
            med = await CurrentMed.create(
                user=user,
                medication_name=drug.standard_drug_name,
                one_dose=f"{drug.dosage_amount or ''}".strip(),
                daily_dose_count=str(drug.daily_frequency or ""),
                one_dose_count="1",  # 기본값
                dose_time=DoseTime.MORNING,
                added_from=AddedFrom.HOSPITAL,
                start_date=str(prescription.prescribed_date or date.today()),
            )
            # 연동 상태 업데이트
            drug.is_linked_to_meds = True
            await drug.save()
            created_meds.append(med)

        return created_meds
