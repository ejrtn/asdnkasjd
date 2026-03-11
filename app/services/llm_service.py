import base64
import json
from typing import Any, cast

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import config
from app.dtos.llm_life_guide import LlmLifeGuideResponse
from app.dtos.ocr import DrugInfo
from app.repositories.llm_life_guide import LLMLifeGuideRepository


class PrescriptionOCRResult(BaseModel):
    hospital_name: str | None
    prescribed_date: str | None
    drugs: list[DrugInfo]
    raw_text: str


class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY) if config.OPENAI_API_KEY else None
        self.default_model = config.CHAT_MODEL
        self._repo = LLMLifeGuideRepository()

    async def analyze_with_schema(self, image_bytes: bytes) -> PrescriptionOCRResult:
        """
        이미지를 분석하여 처방전 정보를 구조화된 Pydantic 모델로 반환합니다.
        """
        if not self.client:
            raise RuntimeError("OpenAI API 키가 설정되지 않았습니다.")

        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        prompt = """
        처방전 또는 진료비 계산서 이미지를 분석하여 다음 정보를 JSON 형식으로 추출해줘.
        1. hospital_name: 병원 이름
        2. prescribed_date: 처방 일자 (YYYY-MM-DD 형식)
        3. drugs: 약품 목록. 각 약품은 drug_name(약품명), dosage(1회 복용량), frequency(1일 복용횟수), duration(복용일수)를 포함해야 함.
        4. raw_text: 이미지에서 추출된 전체 텍스트 (OCR 결과 전체)
        """

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ],
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
        )

        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        return PrescriptionOCRResult(**data)

    async def generate_text(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        if not self.client:
            raise RuntimeError("OpenAI API 키가 설정되지 않았습니다.")

        response = await self.client.chat.completions.create(
            model=model or self.default_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    async def generate_json(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.4,
    ) -> dict[str, Any]:
        if not self.client:
            raise RuntimeError("OpenAI API 키가 설정되지 않았습니다.")

        response = await self.client.chat.completions.create(
            model=model or self.default_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=temperature,
        )

        content = response.choices[0].message.content or "{}"
        return dict(json.loads(content))

    def _to_dto(self, model: Any) -> LlmLifeGuideResponse | None:
        if not model:
            return None
        return LlmLifeGuideResponse(
            user_current_status=model.user_current_status,
            generated_content=model.generated_content,
            activity=model.activity,
            created_at=model.created_at,
        )

    async def get_by_user_id(self, user_id: str) -> LlmLifeGuideResponse | None:
        model = await self._repo.get_by_user_id(user_id=user_id)
        return self._to_dto(model)

    async def update_or_create(self, user_id: str, data: dict) -> LlmLifeGuideResponse:
        model = await self._repo.update_or_create(user_id=user_id, data=data)
        return cast(LlmLifeGuideResponse, self._to_dto(model))
