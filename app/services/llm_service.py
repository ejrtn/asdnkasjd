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

    async def generate_summary(self, prompt: str) -> str:
        """Convenience wrapper for generating a summary from a prompt using the LLM.

        It forwards the prompt as a single user message to `generate_text`.
        """
        return await self.generate_text(messages=[{"role": "user", "content": prompt}])

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
