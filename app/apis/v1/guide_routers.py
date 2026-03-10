from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.security import get_optional_user
from app.dtos.llm_life_guide import LlmLifeGuideResponse
from app.models.user import User
from app.services.guide import GuideService

guide_router = APIRouter(prefix="/guides", tags=["guide"])


@guide_router.post("", response_model=LlmLifeGuideResponse)
async def generate_guide(user: Annotated[User | None, Depends(get_optional_user)] = None):
    service = GuideService()
    user_id = str(user.id) if user and user.id else None
    return await service.generate_guide(user_id)


@guide_router.get("", response_model=LlmLifeGuideResponse)
async def get_guide(user: Annotated[User | None, Depends(get_optional_user)] = None):
    service = GuideService()
    return await service.get_saved_guide(user)


@guide_router.get("/{id}")
async def get_guide_detail(id: int, user: Annotated[User | None, Depends(get_optional_user)] = None):
    return {"id": id, "guide_type": "복약"}


@guide_router.patch("/{id}")
async def update_guide(id: int, user: Annotated[User | None, Depends(get_optional_user)] = None):
    return {"id": id, "detail": "갱신되었습니다."}
