import json
from typing import Any

from openai import AsyncOpenAI

from app.core.config import config


class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY) if config.OPENAI_API_KEY else None
        self.default_model = config.CHAT_MODEL

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
