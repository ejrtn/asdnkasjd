from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.security import get_request_user
from app.dtos.plan_check_list import PlanCheckListRequest, PlanCheckListResponse
from app.models.user import User
from app.services.plan_check_list import PlanCheckListService

plan_check_list = APIRouter(prefix="/plan_check_list", tags=["/plan_check_list"])


@plan_check_list.post("", response_model=PlanCheckListRequest)
async def create_plan_check_list(
    data: PlanCheckListRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    service = PlanCheckListService()
    return await service.create(user.id, data)


@plan_check_list.delete("/{id}")
async def delete_plan_check_list(
    id: int,
    user: Annotated[User, Depends(get_request_user)],
):
    service = PlanCheckListService()
    return await service.delete_by_id(user.id, id)


@plan_check_list.get("", response_model=list[PlanCheckListResponse])
async def get_plan_check_lists(
    user: Annotated[User, Depends(get_request_user)],
):
    service = PlanCheckListService()
    return await service.get_all_by_user(user.id)


@plan_check_list.patch("/{id}/toggle", response_model=PlanCheckListResponse)
async def toggle_plan_check_list(
    id: int,
    user: Annotated[User, Depends(get_request_user)],
):
    service = PlanCheckListService()
    return await service.toggle_completed(user.id, id)


@plan_check_list.post("/sync-alarms")
async def sync_alarms(
    user: Annotated[User, Depends(get_request_user)],
):
    """
    [USER] 현재 활성 알람들을 체크리스트로 동기화 (복구용)
    """
    service = PlanCheckListService()
    await service.sync_pill_plans(user.id)
    return {"detail": "알람 동기화가 완료되었습니다."}


@plan_check_list.post("/recommend-ai")
async def recommend_ai(
    user: Annotated[User, Depends(get_request_user)],
):
    """
    [USER] AI 건강 추천 플랜 생성 및 동기화 (복구/갱신용)
    """
    service = PlanCheckListService()
    await service.sync_llm_plans(user.id)
    return {"detail": "AI 추천 플랜이 생성되었습니다."}
