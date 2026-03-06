from pydantic import BaseModel, Field


class AlarmResponse(BaseModel):
    id: int
    alarm_type: str
    medication_name: str | None = None
    alarm_time: str
    is_active: bool
    current_med_id: int | None = None


class AlarmCreateRequest(BaseModel):
    alarm_type: str = Field(default="MED")
    current_med_id: int | None = Field(None)
    alarm_time: str


class AlarmUpdateRequest(BaseModel):
    alarm_time: str | None = None
    is_active: bool | None = None


class AlarmToggleRequest(BaseModel):
    is_active: bool


class AlarmHistoryResponse(BaseModel):
    history_id: int
    alarm_id: int
    alarm_type: str
    title: str
    body: str
    sent_at: str
    is_confirmed: bool


class DashboardAlarmItemResponse(BaseModel):
    time: str
    label: str
    is_confirmed: bool


class DashboardAlarmSummaryResponse(BaseModel):
    previous_alarm: DashboardAlarmItemResponse | None = None
    next_alarm: DashboardAlarmItemResponse | None = None
    remaining_text: str
