from pydantic import BaseModel


class PlanCheckListResponse(BaseModel):
    content: str
    plan_type: str
    is_completed: bool
    id: int


class PlanCheckListRequest(BaseModel):
    content: str
    plan_type: str = "self"
