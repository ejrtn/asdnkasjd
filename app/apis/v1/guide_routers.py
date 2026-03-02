from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.security import get_optional_user
from app.dtos.guide import GuideResponse
from app.models.user import User
from app.services.guide import GuideService

guide_router = APIRouter(prefix="/guides", tags=["guide"])


@guide_router.post("", response_model=GuideResponse)
async def generate_guide(
    user: Annotated[User | None, Depends(get_optional_user)] = None,
    refresh: bool = False,
):
    service = GuideService()
    return await service.generate_guide(user)


@guide_router.get("")
async def get_guides(user: Annotated[User | None, Depends(get_optional_user)] = None):
    return {"items": []}


@guide_router.get("/{id}")
async def get_guide_detail(id: int, user: Annotated[User | None, Depends(get_optional_user)] = None):
    return {"id": id, "guide_type": "복약"}


@guide_router.patch("/{id}")
async def update_guide(id: int, user: Annotated[User | None, Depends(get_optional_user)] = None):
    return {"guide_id": id, "detail": "갱신되었습니다."}
