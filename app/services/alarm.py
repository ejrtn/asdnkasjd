from datetime import time

from app.dtos.alarm import AlarmCreateRequest, AlarmResponse, AlarmToggleRequest, AlarmUpdateRequest
from app.models.alarm import Alarm
from app.models.current_med import CurrentMed
from app.models.user import User


class AlarmService:
    def _format_time(self, t: object) -> str:
        if hasattr(t, "strftime"):
            return t.strftime("%H:%M")  # type: ignore[union-attr, no-any-return]
        if hasattr(t, "seconds"):  # timedelta
            total = int(t.seconds)  # type: ignore[union-attr]
            return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
        return str(t)

    async def get_user_alarms(self, user: User) -> list[AlarmResponse]:
        alarms = await Alarm.filter(user=user).prefetch_related("current_med")
        return [
            AlarmResponse(
                id=alarm.id,
                medication_name=alarm.current_med.medication_name if alarm.current_med else "알 수 없음",
                alarm_time=self._format_time(alarm.alarm_time),
                is_active=alarm.is_active,
                current_med_id=alarm.current_med.id if alarm.current_med else 0,
            )
            for alarm in alarms
        ]

    async def create_alarm(self, user: User, request: AlarmCreateRequest) -> AlarmResponse:
        current_med = await CurrentMed.get_or_none(id=request.current_med_id, user=user)
        if not current_med:
            raise ValueError("해당 약물을 찾을 수 없습니다.")

        hour, minute = map(int, request.alarm_time.split(":"))
        alarm = await Alarm.create(user=user, current_med=current_med, alarm_time=time(hour, minute), is_active=True)

        return AlarmResponse(
            id=alarm.id,
            medication_name=current_med.medication_name,
            alarm_time=request.alarm_time,
            is_active=True,
            current_med_id=current_med.id,
        )

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

        return AlarmResponse(
            id=alarm.id,
            medication_name=alarm.current_med.medication_name if alarm.current_med else "알 수 없음",
            alarm_time=self._format_time(alarm.alarm_time),
            is_active=alarm.is_active,
            current_med_id=alarm.current_med.id if alarm.current_med else 0,
        )

    async def toggle_alarm(self, user: User, alarm_id: int, request: AlarmToggleRequest) -> AlarmResponse:
        alarm = await Alarm.get_or_none(id=alarm_id, user=user)
        if not alarm:
            raise ValueError("알람을 찾을 수 없습니다.")
        await alarm.fetch_related("current_med")

        alarm.is_active = request.is_active
        await alarm.save()

        return AlarmResponse(
            id=alarm.id,
            medication_name=alarm.current_med.medication_name if alarm.current_med else "알 수 없음",
            alarm_time=self._format_time(alarm.alarm_time),
            is_active=alarm.is_active,
            current_med_id=alarm.current_med.id if alarm.current_med else 0,
        )

    async def delete_alarm(self, user: User, alarm_id: int) -> None:
        alarm = await Alarm.get_or_none(id=alarm_id, user=user)
        if not alarm:
            raise ValueError("알람을 찾을 수 없습니다.")

        await alarm.delete()
