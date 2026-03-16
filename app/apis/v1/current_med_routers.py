from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.security import get_request_user
from app.dtos.health import CurrentMedResponse, CurrentMedSaveRequest
from app.models.current_med import CurrentMed
from app.models.user import User

current_med_router = APIRouter(prefix="/current-meds", tags=["current_med"])


@current_med_router.get("", response_model=list[CurrentMedResponse])
async def get_current_meds(user: Annotated[User, Depends(get_request_user)]) -> list[CurrentMedResponse]:
    """현재 복용 중인 약물 목록 조회"""
    meds = await CurrentMed.filter(user=user)
    return [
        CurrentMedResponse(
            id=med.id,
            medication_name=med.medication_name,
            one_dose_amount=med.one_dose_amount,
            one_dose_count=med.one_dose_count,
            total_days=med.total_days,
            instructions=med.instructions,
        )
        for med in meds
    ]


@current_med_router.post("", status_code=status.HTTP_201_CREATED, response_model=CurrentMedResponse)
async def create_current_med(
    request: CurrentMedSaveRequest, user: Annotated[User, Depends(get_request_user)]
) -> CurrentMedResponse:
    """현재 복용약 수기 등록"""
    med = await CurrentMed.create(
        user=user,
        medication_name=request.medication_name,
        one_dose_amount=request.one_dose_amount,
        one_dose_count=request.one_dose_count,
        total_days=request.total_days,
        instructions=request.instructions,
    )

    return CurrentMedResponse(
        id=med.id,
        medication_name=med.medication_name,
        one_dose_amount=med.one_dose_amount,
        one_dose_count=med.one_dose_count,
        total_days=med.total_days,
        instructions=med.instructions,
    )


@current_med_router.delete("/{med_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_med(med_id: int, user: Annotated[User, Depends(get_request_user)]) -> None:
    """현재 복용약 삭제"""
    med = await CurrentMed.get_or_none(id=med_id, user=user)
    if not med:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="약물을 찾을 수 없습니다.")

    await med.delete()
