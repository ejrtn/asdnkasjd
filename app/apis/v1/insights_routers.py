import json
import logging
import os

import httpx
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/insights", tags=["insights"])

FALLBACK = {
    "insights": [
        "물 한 잔으로 오늘을 가볍게 시작해요.",
        "스트레칭 3분이면 몸이 훨씬 편해져요.",
        "잠들기 30분 전 화면을 줄이면 숙면에 도움돼요.",
    ]
}


@router.get("/health")
async def get_health_insights(user_id: str | None = None):
    """건강 인사이트를 생성합니다. 로그인 시 사용자 정보 기반, 미로그인 시 일반 인사이트."""

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.warning("[Insights] OPENAI_API_KEY is not set, returning fallback")
        return FALLBACK

    if user_id:
        logger.info(f"[Insights] Loading personalized insights for user: {user_id}")
        prompt = f"""사용자 ID: {user_id}의 건강 프로필을 바탕으로 오늘의 건강 인사이트 3줄을 작성해주세요.

요구사항:
- 각 줄은 50자 이내
- 긍정적이고 실행 가능한 조언
- 반드시 아래 JSON 형식만 출력
{{"insights":["줄1","줄2","줄3"]}}"""
    else:
        logger.info("[Insights] Loading general insights (not logged in)")
        prompt = """모든 사람에게 어울리는 오늘의 건강 인사이트 3줄을 작성해주세요.

요구사항:
- 각 줄은 50자 이내
- 긍정적이고 실행 가능한 조언
- 반드시 아래 JSON 형식만 출력
{"insights":["줄1","줄2","줄3"]}"""

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 200,
                    "response_format": {"type": "json_object"},
                },
            )
            r.raise_for_status()
            data = r.json()

        content = data["choices"][0]["message"]["content"]

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"[Insights] JSON parse failed, content={content!r}")
            return FALLBACK

        if not isinstance(parsed, dict) or "insights" not in parsed or len(parsed.get("insights", [])) != 3:
            logger.warning(f"[Insights] Invalid response format: {parsed}")
            return FALLBACK

        logger.info(f"[Insights] Successfully generated: {parsed['insights']}")
        return parsed

    except httpx.HTTPStatusError as e:
        logger.error(f"[Insights] OpenAI API error: {e.response.status_code} - {e.response.text}")
        return FALLBACK
    except Exception as e:
        logger.error(f"[Insights] Unexpected error: {str(e)}")
        return FALLBACK
