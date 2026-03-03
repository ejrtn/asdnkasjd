from datetime import time

from app.dtos.alarm import AlarmCreateRequest, AlarmResponse, AlarmToggleRequest, AlarmUpdateRequest
from app.models.alarm import Alarm
from app.models.current_med import CurrentMed
from app.models.user import User

HEALTH_ALARM_NAMES = {
    "BP_MORNING": "혈압 아침 측정",
    "BP_EVENING": "혈압 저녁 측정",
    "BS_FASTING": "혈당 공복 측정",
    "BS_POSTMEAL": "혈당 식후 2시간",
    "BS_BEDTIME": "혈당 취침 전",
}


class AlarmService:
    def _format_time(self, t: object) -> str:
        if hasattr(t, "strftime"):
            return t.strftime("%H:%M")  # type: ignore[union-attr, no-any-return]
        if hasattr(t, "seconds"):  # timedelta
            total = int(t.seconds)  # type: ignore[union-attr]
            return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
        return str(t)

    def _to_response(self, alarm: Alarm, med_name: str, med_id: int) -> AlarmResponse:
        return AlarmResponse(
            id=alarm.id,
            alarm_type=alarm.alarm_type,
            medication_name=med_name,
            alarm_time=self._format_time(alarm.alarm_time),
            is_active=alarm.is_active,
            current_med_id=med_id,
        )

    async def get_user_alarms(self, user: User, alarm_type: str | None = None) -> list[AlarmResponse]:
        qs = Alarm.filter(user=user)
        if alarm_type:
            qs = qs.filter(alarm_type=alarm_type)
        alarms = await qs.prefetch_related("current_med")
        return [
            self._to_response(
                alarm,
                HEALTH_ALARM_NAMES.get(
                    alarm.alarm_type, alarm.current_med.medication_name if alarm.current_med else "알 수 없음"
                ),
                alarm.current_med.id if alarm.current_med else 0,
            )
            for alarm in alarms
        ]

    async def create_alarm(self, user: User, request: AlarmCreateRequest) -> AlarmResponse:
        current_med = None
        med_name = HEALTH_ALARM_NAMES.get(request.alarm_type, "알 수 없음")
        med_id = 0

        if request.alarm_type == "MED":
            if not request.current_med_id:
                raise ValueError("복약 알람은 약물 ID가 필요합니다.")
            current_med = await CurrentMed.get_or_none(id=request.current_med_id, user=user)
            if not current_med:
                raise ValueError("해당 약물을 찾을 수 없습니다.")
            med_name = current_med.medication_name
            med_id = current_med.id

        hour, minute = map(int, request.alarm_time.split(":"))
        alarm = await Alarm.create(
            user=user,
            alarm_type=request.alarm_type,
            current_med=current_med,
            alarm_time=time(hour, minute),
            is_active=True,
        )
        return self._to_response(alarm, med_name, med_id)

    async def update_alarm(self, user: User, alarm_id: int, request: AlarmUpdateRequest) -> AlarmResponse:
        alarm = await Alarm.get_or_none(id=alarm_id, user=user)
        if not alarm:
            raise ValueError("알람을 찾을 수 없습니다.")
        await alarm.fetch_related("current_med")

        if request.alarm_time:
            hour, minute = map(int, request.alarm_time.split(":"))
            alarm.alarm_time = time(hour, minute)
        if request.is_active is not None:
            alarm.is_active = request.is_active
        await alarm.save()

        med_name = HEALTH_ALARM_NAMES.get(
            alarm.alarm_type, alarm.current_med.medication_name if alarm.current_med else "알 수 없음"
        )
        return self._to_response(alarm, med_name, alarm.current_med.id if alarm.current_med else 0)

    async def toggle_alarm(self, user: User, alarm_id: int, request: AlarmToggleRequest) -> AlarmResponse:
        alarm = await Alarm.get_or_none(id=alarm_id, user=user)
        if not alarm:
            raise ValueError("알람을 찾을 수 없습니다.")
        await alarm.fetch_related("current_med")

        alarm.is_active = request.is_active
        await alarm.save()

        med_name = HEALTH_ALARM_NAMES.get(
            alarm.alarm_type, alarm.current_med.medication_name if alarm.current_med else "알 수 없음"
        )
        return self._to_response(alarm, med_name, alarm.current_med.id if alarm.current_med else 0)

    async def delete_alarm(self, user: User, alarm_id: int) -> None:
        alarm = await Alarm.get_or_none(id=alarm_id, user=user)
        if not alarm:
            raise ValueError("알람을 찾을 수 없습니다.")
        await alarm.delete()
