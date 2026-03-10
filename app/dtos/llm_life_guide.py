# guide.py : 프론트 응답용 / llm_life_guide.py : DB 저장용
from datetime import datetime

from pydantic import BaseModel


class LlmLifeGuideResponse(BaseModel):
    user_current_status: str
    generated_content: dict
    activity: bool
    created_at: datetime


class LlmLifeGuideRequest(BaseModel):
    user_current_status: str
    activity: bool
    generated_content: dict
