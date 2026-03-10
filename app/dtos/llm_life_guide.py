from datetime import datetime

from pydantic import BaseModel


class LlmLifeGuideResponse(BaseModel):
    user_current_status: str
    generated_content: str
    created_at: datetime


class LlmLifeGuideRequest(BaseModel):
    user_current_status: str
    generated_content: str
    created_at: datetime
