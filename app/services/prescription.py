import asyncio
import json
import logging
from datetime import date
from typing import Any

from openai import AsyncOpenAI

from app.core import config
from app.models.current_med import CurrentMed
from app.models.ocr_history import OCRHistory
from app.models.prescription import Prescription
from app.models.prescription_drug import PrescriptionDrug
from app.models.upload import Upload
from app.models.user import User
from app.repositories.prescription import PrescriptionRepository
from app.services.guide import GuideService

logger = logging.getLogger(__name__)


class PrescriptionService:
    """
    LLM을 사용하여 처방전의 OCR 텍스트를 파싱하고 정제된 데이터를 관리하는 서비스 클래스입니다.
    """

    def __init__(self):
        self.repo = PrescriptionRepository()
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.guide_service = GuideService()

    @staticmethod
    def _clean_drug_name(raw_name: str) -> str:
        """
        약품명에서 불필요한 접두어(비), 급)) 및 잘린 괄호/성분명을 제거하고 특수기호를 제외합니다.
        """
        import re

        if not raw_name:
            return ""

        # 1. '비)' 또는 '급)' 제거
        name = re.sub(r"^[비급]\)\s*", "", raw_name)
        # 2. 첫 번째 괄호가 시작되는 지점 이후로 모두 제거 (잘린 성성분명/용량 제거)
        name = name.split("(")[0]
        # 3. 불필요한 특수문자 제거
        name = re.sub(r"[^가-힣a-zA-Z0-9\s]", "", name)
        # 4. 양끝 공백 제거
        return name.strip()

    def _preprocess_image(self, image_bytes: bytes) -> bytes:
        """
        [성능 향상] 이미지 대비와 선명도를 높여 OCR 인식률을 개선합니다.
        """
        import io

        from PIL import Image, ImageEnhance, ImageOps

        try:
            # 1. 처음에 여는 이미지 변수 이름을 'source_img'로 합니다. (ImageFile 타입)
            source_img = Image.open(io.BytesIO(image_bytes))

            # 2. 가공을 시작하는 시점부터는 'processed'라는 새로운 변수 이름을 씁니다. (Image 타입)
            # 이렇게 이름을 아예 갈라치면 mypy가 더 이상 화내지 않습니다.
            img_for_processing = source_img.convert("RGB") if source_img.mode != "RGB" else source_img
            processed = ImageOps.grayscale(img_for_processing)

            # 3. 대비(Contrast) 향상
            enhancer = ImageEnhance.Contrast(processed)
            processed = enhancer.enhance(2.5)

            # 4. 선명도(Sharpness) 조절
            sharpness = ImageEnhance.Sharpness(processed)
            processed = sharpness.enhance(2.0)

            # 바이트로 다시 변환
            img_byte_arr = io.BytesIO()
            processed.save(img_byte_arr, format="JPEG", quality=95)
            return img_byte_arr.getvalue()
        except Exception as e:
            logger.error(f"이미지 전처리 실패: {e}")
            return image_bytes

    async def parse_prescription_with_vision(self, image_bytes: bytes) -> dict[str, Any]:
        """
        GPT-4o-mini Vision을 사용하여 처방전 이미지를 직접 분석하고 구조화된 데이터를 추출합니다.
        회전되거나 뒤집힌 이미지도 자동으로 처리하며, 노이즈를 효과적으로 필터링합니다.
        """
        import base64

        if not config.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY가 설정되지 않았습니다. 파싱을 건너뜁니다.")
            return {"hospital_name": None, "prescribed_date": None, "drugs": []}

        # 전처리 적용
        processed_bytes = self._preprocess_image(image_bytes)
        image_b64 = base64.b64encode(processed_bytes).decode("utf-8")

        system_prompt = """
        당신은 한국의 처방전 및 약봉투 분석 전문가입니다. 이미지를 보고 '병원/약국명', '날짜', '약물 정보'를 JSON으로 추출하세요.

        ### [추출 및 정제 규칙] ###
        1. **약품명 정제 (CRITICAL)**:
           - 이름 앞의 '비)', '급)' 등 급여 구분 기호는 반드시 제거하세요.
           - 이름 뒤에 잘린 괄호나 성분명(예: '(독시사이클린수')은 제거하고 순수 제품명만 남기세요.
           - 예: "비)바이독시정(독시사이클린수" -> "바이독시정"
           - 예: "비)생생장캡슐(바실루스리케니" -> "생생장캡슐"
        2. **복약안내 제외**: '세균감염증 치료제', '정장제'와 같은 설명문은 `name`에 절대 포함하지 마세요.
        3. **수치 데이터**: 투약량(1.00), 횟수(2), 일수(10)를 정확히 숫자로 매핑하세요.
        4. **방향 무관**: 사진이 거꾸로 되어 있어도 글자 방향을 읽어 정확히 파악하세요.

        ### JSON OUTPUT FORMAT ###
        {
            "hospital_name": "병원명 또는 약국명 (null 가능)",
            "prescribed_date": "YYYY-MM-DD (null 가능)",
            "drug_list_raw": "추출된 약물 이름들 (쉼표 구분)",
            "drugs": [
                {
                    "name": "바이독시정",
                    "dosage": 1.0,
                    "frequency": 2,
                    "duration": 10
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

        # 2. 약품명 2차 정제 (Python 레벨 후처리)
        if drug_list_raw:
            cleaned_names = [self._clean_drug_name(name) for name in drug_list_raw.split(",") if name.strip()]
            drug_list_raw = ", ".join(cleaned_names)

        for drug in drugs_data:
            if "name" in drug:
                drug["name"] = self._clean_drug_name(drug["name"])

        # 3. 날짜 형식 검증
        prescribed_date = None
        if prescribed_date_str:
            try:
                prescribed_date = date.fromisoformat(prescribed_date_str)
            except ValueError:
                logger.warning(f"잘못된 날짜 형식: {prescribed_date_str}")

        # 4. OCRHistory 생성 (Vision 분석 원본 결과 저장)
        ocr_history = await OCRHistory.create(
            user=user,
            raw_text=json.dumps(parsed_data, ensure_ascii=False),
            is_valid=True,
            front_upload=upload,
            inference_metadata={"model": "gpt-4o-mini-vision"},
        )

        # 5. Prescription 생성
        prescription = await self.repo.create(
            user=user,
            upload=upload,
            ocr_history=ocr_history,
            hospital_name=hospital_name,
            prescribed_date=prescribed_date,
            drug_list_raw=drug_list_raw,
        )

        # 6. PrescriptionDrug 생성
        async def _save_drug(drug):
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

        await asyncio.gather(*(_save_drug(d) for d in drugs_data))

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
        async def _save_drug_logic(drug, is_raw=False):
            try:
                name = drug if is_raw else drug.get("name")
                await self.repo.create_drug(
                    prescription=prescription,
                    standard_drug_name=name,
                    dosage_amount=None if is_raw else drug.get("dosage"),
                    daily_frequency=None if is_raw else drug.get("frequency"),
                    duration_days=None if is_raw else drug.get("duration"),
                )
            except Exception as e:
                logger.error(f"약물 데이터 저장 실패: {drug}, 에러: {str(e)}")

        if not drugs_data and drug_list_raw:
            raw_drugs = [name.strip() for name in drug_list_raw.split(",") if name.strip()]
            await asyncio.gather(*(_save_drug_logic(name, is_raw=True) for name in raw_drugs))
        else:
            await asyncio.gather(*(_save_drug_logic(d) for d in drugs_data))

        return prescription

    async def sync_to_current_meds(
        self, prescription_id: int, user: User, drug_names: list[str] | None = None
    ) -> list[Any]:
        """
        [Step 6] 처방전의 약물들을 현재 복용 중인 약물(CurrentMed) 테이블로 복사(연동)합니다.
        drug_names가 제공될 경우 해당 약물들만 선택하여 연동합니다.
        """

        prescription = await self.repo.get_by_id(prescription_id)
        if not prescription or prescription.user_id != user.id:
            raise ValueError("처방전을 찾을 수 없거나 권한이 없습니다.")

        drugs = await prescription.drugs.all()

        async def _sync_drug(drug):
            # 선택된 약물 리스트가 있다면 필터링
            if drug_names is not None and drug.standard_drug_name not in drug_names:
                return None

            # 새로운 5가지 필드에 맞춰 데이터 연동
            med = await CurrentMed.create(
                user=user,
                medication_name=drug.standard_drug_name,
                one_dose_amount=f"{drug.dosage_amount or ''}".strip(),
                one_dose_count=str(drug.daily_frequency or ""),
                total_days=str(drug.duration_days or ""),
                instructions="",
            )
            # 연동 상태 업데이트 및 관계 설정 [FIX]
            drug.is_linked_to_meds = True
            drug.current_med = med
            await drug.save()
            return med

        # 병렬 동기화 실행
        results = await asyncio.gather(*(_sync_drug(d) for d in drugs))

        return [r for r in results if r is not None]

    async def toggle_med_sync(self, prescription_id: int, user: User, drug_name: str) -> dict[str, Any]:
        """
        처방전의 특정 약물을 current_meds에 추가하거나 제거합니다(토글).
        - prescriptions / prescription_drugs / ocr_history 는 LLM 분석 시 1회 저장 전용이므로 절대 수정하지 않음.
        - current_meds 테이블만 추가/삭제합니다.
        """
        # 1. 처방전 조회 (user 조건 포함하여 권한 검증)
        prescription = await Prescription.filter(id=prescription_id, user=user).first()

        if not prescription:
            # Upload ID로 잘못 전달된 경우 보정
            upload = await Upload.filter(id=prescription_id, user=user).first()
            if upload:
                prescription = await Prescription.filter(upload=upload, user=user).first()

            if not prescription:
                logger.error(f"[toggle_med_sync] Prescription not found: user={user.id}, id={prescription_id}")
                raise ValueError("처방전을 찾을 수 없거나 권한이 없습니다.")

        # 2. 해당 처방전의 약물 조회 (prescription_drugs는 읽기 전용)
        drug_name_cleaned = drug_name.strip()
        drug = await PrescriptionDrug.filter(
            prescription=prescription,
            standard_drug_name=drug_name_cleaned,
        ).first()
        if not drug:
            drug = await PrescriptionDrug.filter(
                prescription=prescription,
                standard_drug_name=drug_name,
            ).first()
        if not drug:
            logger.error(f"[toggle_med_sync] Drug not found: '{drug_name}' in prescription {prescription_id}")
            raise ValueError(f"처방전에서 '{drug_name}' 약물을 찾을 수 없습니다.")

        # 3. current_meds에서 현재 등록 여부 확인 (user + medication_name 기준)
        existing_med = await CurrentMed.filter(
            user=user,
            medication_name=drug.standard_drug_name,
        ).first()

        if existing_med:
            # 토글 오프: current_meds에서 삭제만 (prescription_drugs 건드리지 않음)
            await existing_med.delete()
            return {"synced": False, "message": f"'{drug_name}'이(가) 복용 목록에서 제거되었습니다."}
        else:
            # 토글 온: current_meds에 추가만 (prescription_drugs 건드리지 않음)
            await CurrentMed.create(
                user=user,
                medication_name=drug.standard_drug_name,
                one_dose_amount=f"{drug.dosage_amount or ''}".strip(),
                one_dose_count=str(drug.daily_frequency or ""),
                total_days=str(drug.duration_days or ""),
                instructions="",
            )
            return {"synced": True, "message": f"'{drug_name}'이(가) 복용 목록에 추가되었습니다."}
