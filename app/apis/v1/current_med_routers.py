from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies.security import get_request_user
from app.models.current_med import CurrentMed
from app.models.user import User

current_med_router = APIRouter(prefix="/current-meds", tags=["current_med"])


class CurrentMedResponse(BaseModel):
    id: int
    medication_name: str
    added_from: str
    start_date: str


class CurrentMedCreateRequest(BaseModel):
    medication_name: str = Field(..., description="약물 이름")
    added_from: str = Field(default="MANUAL", description="추가 경로")


@current_med_router.get("", response_model=list[CurrentMedResponse])
async def get_current_meds(user: Annotated[User, Depends(get_request_user)]) -> list[CurrentMedResponse]:
    """현재 복용 중인 약물 목록 조회"""
    meds = await CurrentMed.filter(user=user)
    return [
        CurrentMedResponse(
            id=med.id,
            medication_name=med.medication_name,
            added_from=med.added_from,
            start_date=str(med.start_date),
        )
        for med in meds
    ]


@current_med_router.post("", status_code=status.HTTP_201_CREATED, response_model=CurrentMedResponse)
async def create_current_med(
    request: CurrentMedCreateRequest, user: Annotated[User, Depends(get_request_user)]
) -> CurrentMedResponse:
    """현재 복용약 수기 등록"""
    from datetime import date

    med = await CurrentMed.create(
        user=user,
        medication_name=request.medication_name,
        added_from=request.added_from,
        start_date=date.today(),
    )

    return CurrentMedResponse(
        id=med.id,
        medication_name=med.medication_name,
        added_from=med.added_from,
        start_date=str(med.start_date),
    )


@current_med_router.delete("/{med_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_med(med_id: int, user: Annotated[User, Depends(get_request_user)]) -> None:
    """현재 복용약 삭제"""
    med = await CurrentMed.get_or_none(id=med_id, user=user)
    if not med:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="약물을 찾을 수 없습니다.")

    await med.delete()
