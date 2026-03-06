from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.security import get_request_user
from app.dtos.health import (
    BloodPressureRequest,
    BloodSugarRequest,
    FullHealthProfileSaveRequest,
    HealthProfileResponse,
)
from app.models.user import User
from app.services.blood_pressure_record import BloodPressureRecordService
from app.services.blood_sugar_record import BloodSugarRecordService
from app.services.health_profile import HealthProfileService

health_router = APIRouter(prefix="/health", tags=["health-profile"])


@health_router.get("", response_model=HealthProfileResponse)
async def get_health_profile(
    user: Annotated[User | None, Depends(get_request_user)] = None,
    refresh: bool = False,
):
    service = HealthProfileService()
    return await service.generate_health_profile(user)


@health_router.post("")
async def create_health_profile(
    request: FullHealthProfileSaveRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    service = HealthProfileService()
    return await service.save_full_health_profile(user.id, request)


@health_router.put("", response_model=HealthProfileResponse)
async def update_health_profile(
    user: Annotated[User | None, Depends(get_request_user)] = None,
    refresh: bool = False,
):
    service = HealthProfileService()
    return await service.generate_health_profile(user)


@health_router.post("/blood-sugar")
async def create_blood_sugar(
    request: BloodSugarRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    service = HealthProfileService()
    return await service.blood_sugar_save(request, user.id)


@health_router.get("/blood-sugar")
async def get_blood_sugar(
    user: Annotated[User, Depends(get_request_user)],
):
    service = BloodSugarRecordService()
    return await service.generate_blood_sugar(user)


@health_router.post("/blood-pressure")
async def create_blood_pressure(
    request: BloodPressureRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    service = HealthProfileService()
    return await service.blood_pressure_save(request, user.id)


@health_router.get("/blood-pressure")
async def get_blood_pressure(
    user: Annotated[User, Depends(get_request_user)],
):
    service = BloodPressureRecordService()
    return await service.generate_blood_pressure(user)
