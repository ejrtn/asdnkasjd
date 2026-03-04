from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.security import get_request_user
from app.dtos.health import (
    HealthProfileResponse,
)
from app.models.user import User
from app.services.health_profile import HealthProfileService

health_router = APIRouter(prefix="/health", tags=["health-profile"])


@health_router.get("", response_model=HealthProfileResponse)
async def get_health_profile(
    user: Annotated[User | None, Depends(get_request_user)] = None,
    refresh: bool = False,
):
    service = HealthProfileService()
    return await service.generate_health_profile(user)


@health_router.post("", response_model=HealthProfileResponse)
async def create_health_profile(
    user: Annotated[User | None, Depends(get_request_user)] = None,
    refresh: bool = False,
):
    service = HealthProfileService()
    return await service.generate_health_profile(user)


@health_router.put("", response_model=HealthProfileResponse)
async def update_health_profile(
    user: Annotated[User | None, Depends(get_request_user)] = None,
    refresh: bool = False,
):
    service = HealthProfileService()
    return await service.generate_health_profile(user)
