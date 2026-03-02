from pydantic import BaseModel, Field


class AlarmResponse(BaseModel):
    id: int = Field(..., description="알람 ID")
    medication_name: str = Field(..., description="약물 이름")
    alarm_time: str = Field(..., description="알람 시간 (HH:MM)")
    is_active: bool = Field(..., description="알람 활성화 여부")
    current_med_id: int = Field(..., description="연동된 약물 ID")


class AlarmCreateRequest(BaseModel):
    current_med_id: int = Field(..., description="약물 ID")
    alarm_time: str = Field(..., description="알람 시간 (HH:MM)")


class AlarmUpdateRequest(BaseModel):
    alarm_time: str | None = Field(None, description="알람 시간 (HH:MM)")
    is_active: bool | None = Field(None, description="알람 활성화 여부")


class AlarmToggleRequest(BaseModel):
    is_active: bool = Field(..., description="알람 활성화 여부")
