from datetime import time

from app.dtos.alarm import AlarmCreateRequest, AlarmResponse, AlarmToggleRequest, AlarmUpdateRequest
from app.models.alarm import Alarm
from app.models.current_med import CurrentMed
from app.models.user import User


class AlarmService:
    async def get_user_alarms(self, user: User) -> list[AlarmResponse]:
        """사용자의 모든 알람 조회"""
        alarms = await Alarm.filter(user=user).prefetch_related("current_med")
        return [
            AlarmResponse(
                id=alarm.id,
                medication_name=alarm.current_med.medication_name if alarm.current_med else "알 수 없음",
                alarm_time=str(alarm.alarm_time) if isinstance(alarm.alarm_time, str) else alarm.alarm_time.strftime("%H:%M") if hasattr(alarm.alarm_time, 'strftime') else str(alarm.alarm_time),
                is_active=alarm.is_active,
                current_med_id=alarm.current_med.id if alarm.current_med else 0,
            )
            for alarm in alarms
        ]

    async def create_alarm(self, user: User, request: AlarmCreateRequest) -> AlarmResponse:
        """새 알람 생성"""
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
        """알람 수정"""
        alarm = await Alarm.get_or_none(id=alarm_id, user=user).prefetch_related("current_med")
        if not alarm:
            raise ValueError("알람을 찾을 수 없습니다.")

        if request.alarm_time:
            hour, minute = map(int, request.alarm_time.split(":"))
            alarm.alarm_time = time(hour, minute)

        if request.is_active is not None:
            alarm.is_active = request.is_active

        await alarm.save()

        return AlarmResponse(
            id=alarm.id,
            medication_name=alarm.current_med.medication_name if alarm.current_med else "알 수 없음",
            alarm_time=alarm.alarm_time.strftime("%H:%M"),
            is_active=alarm.is_active,
            current_med_id=alarm.current_med.id if alarm.current_med else 0,
        )

    async def toggle_alarm(self, user: User, alarm_id: int, request: AlarmToggleRequest) -> AlarmResponse:
        """알람 온/오프 토글"""
        alarm = await Alarm.get_or_none(id=alarm_id, user=user).prefetch_related("current_med")
        if not alarm:
            raise ValueError("알람을 찾을 수 없습니다.")

        alarm.is_active = request.is_active
        await alarm.save()

        return AlarmResponse(
            id=alarm.id,
            medication_name=alarm.current_med.medication_name if alarm.current_med else "알 수 없음",
            alarm_time=alarm.alarm_time.strftime("%H:%M"),
            is_active=alarm.is_active,
            current_med_id=alarm.current_med.id if alarm.current_med else 0,
        )

    async def delete_alarm(self, user: User, alarm_id: int) -> None:
        """알람 삭제"""
        alarm = await Alarm.get_or_none(id=alarm_id, user=user)
        if not alarm:
            raise ValueError("알람을 찾을 수 없습니다.")

        await alarm.delete()
