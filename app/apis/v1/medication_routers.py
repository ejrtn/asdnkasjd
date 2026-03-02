from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.security import get_optional_user, get_request_user
from app.models.user import User

medication_router = APIRouter(tags=["medication"])


@medication_router.patch("/medications/confirm/drug/{id}")
async def confirm_drug(id: int, user: Annotated[User, Depends(get_request_user)]):
    """
    [CONFIRM] 처방전 약물 승인.
    """
    return {"detail": "승인되었습니다.", "current_meds_id": 1001}


@medication_router.patch("/medications/confirm/pill/{id}")
async def confirm_pill(id: int, user: Annotated[User, Depends(get_request_user)]):
    """
    [CONFIRM] 알약 인식 승인.
    """
    return {"detail": "승인되었습니다.", "current_meds_id": 1002}
