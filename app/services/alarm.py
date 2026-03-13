from datetime import date, datetime, time, timedelta
from typing import cast
from zoneinfo import ZoneInfo

from app.dtos.alarm import (
    AlarmCreateRequest,
    AlarmHistoryResponse,
    AlarmResponse,
    AlarmToggleRequest,
    AlarmUpdateRequest,
    DashboardAlarmItemResponse,
    DashboardAlarmSummaryResponse,
)
from app.models.alarm import Alarm
from app.models.alarm_history import AlarmHistory
from app.models.current_med import CurrentMed
from app.models.user import User
from app.repositories.current_med import CurrentMedRepository
from app.repositories.plan_check_list import PlanCheckListRepository
from app.services.plan_check_list import PlanCheckListService

HEALTH_ALARM_NAMES = {
    "BP_MORNING": "혈압 아침 측정",
    "BP_EVENING": "혈압 저녁 측정",
    "BS_FASTING": "혈당 공복 측정",
    "BS_POSTMEAL": "혈당 식후 2시간",
    "BS_BEDTIME": "혈당 취침 전",
}


class AlarmService:
    def __init__(self):
        self.plan_check_list_repo = PlanCheckListRepository()
        self.current_med = CurrentMedRepository()

    def _format_time(self, t: object) -> str:
        if hasattr(t, "strftime"):
            return t.strftime("%H:%M")  # type: ignore[union-attr, no-any-return]
        if hasattr(t, "seconds"):  # timedelta
            total = int(t.seconds)  # type: ignore[union-attr]
            return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
        return str(t)

    def _normalize_alarm_time(self, value: object) -> time:
        if isinstance(value, time):
            return value

        if hasattr(value, "seconds"):  # timedelta 대응
            total = int(value.seconds)  # type: ignore[union-attr]
            hour = (total // 3600) % 24
            minute = (total % 3600) // 60
            second = total % 60
            return time(hour, minute, second)

        if isinstance(value, str):
            parts = value.split(":")
            hour = int(parts[0])
            minute = int(parts[1])
            second = int(parts[2]) if len(parts) > 2 else 0
            return time(hour, minute, second)

        raise ValueError(f"지원하지 않는 alarm_time 타입입니다: {type(value)}")

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

        # 복약 체크리스트 동기화 (plan_type='pill')
        if request.alarm_type == "MED":
            plan_service = PlanCheckListService()
            await plan_service.sync_pill_plans(user.id)

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

        # 복약 체크리스트 동기화 (plan_type='pill')
        if alarm.alarm_type == "MED":
            plan_service = PlanCheckListService()
            await plan_service.sync_pill_plans(user.id)

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

        # 복약 체크리스트 동기화 (plan_type='pill')
        if alarm.alarm_type == "MED":
            plan_service = PlanCheckListService()
            await plan_service.sync_pill_plans(user.id)

        med_name = HEALTH_ALARM_NAMES.get(
            alarm.alarm_type, alarm.current_med.medication_name if alarm.current_med else "알 수 없음"
        )
        return self._to_response(alarm, med_name, alarm.current_med.id if alarm.current_med else 0)

    async def delete_alarm(self, user: User, alarm_id: int) -> None:
        alarm = await Alarm.get_or_none(id=alarm_id, user=user)
        if not alarm:
            raise ValueError("알람을 찾을 수 없습니다.")
        await alarm.delete()

        # 복약 체크리스트 동기화 (plan_type='pill')
        if alarm.alarm_type == "MED":
            plan_service = PlanCheckListService()
            await plan_service.sync_pill_plans(user.id)

    def _get_dashboard_alarm_label(self, alarm: Alarm) -> str:
        if alarm.alarm_type == "MED":
            return cast(str, alarm.current_med.medication_name if alarm.current_med else "복약 알람")

        label_map: dict[str, str] = {
            "BP_MORNING": "아침 혈압 측정",
            "BP_EVENING": "저녁 혈압 측정",
            "BS_FASTING": "아침 공복 혈당",
            "BS_POSTMEAL": "식후 2시간 혈당",
            "BS_BEDTIME": "취침 전 혈당",
        }
        return cast(str, label_map.get(alarm.alarm_type, "알람"))

    def _build_alarm_datetime_kst(self, alarm: Alarm, target_date: date) -> datetime:
        normalized_time = self._normalize_alarm_time(alarm.alarm_time)
        return datetime.combine(
            target_date,
            normalized_time,
            tzinfo=ZoneInfo("Asia/Seoul"),
        )

    def _format_remaining_text(self, target_dt: datetime, now: datetime) -> str:
        diff = target_dt - now
        total_minutes = max(0, int(diff.total_seconds() // 60))
        hours = total_minutes // 60
        minutes = total_minutes % 60

        if total_minutes == 0:
            return "곧 다음 알림이 울립니다."
        if hours == 0:
            return f"다음 알림까지 {minutes}분 남음"
        if minutes == 0:
            return f"다음 알림까지 {hours}시간 남음"
        return f"다음 알림까지 {hours}시간 {minutes}분 남음"

    async def get_dashboard_alarm_summary(self, user: User) -> DashboardAlarmSummaryResponse:
        now = datetime.now(ZoneInfo("Asia/Seoul"))
        today = now.date()
        tomorrow = today + timedelta(days=1)

        alarms = await Alarm.filter(user=user, is_active=True).prefetch_related("current_med").order_by("alarm_time")

        if not alarms:
            return DashboardAlarmSummaryResponse(
                previous_alarm=None, next_alarm=None, remaining_text="예정된 다음 알림이 없습니다."
            )

        today_items: list[tuple[datetime, Alarm]] = []
        tomorrow_items: list[tuple[datetime, Alarm]] = []

        for alarm in alarms:
            today_items.append((self._build_alarm_datetime_kst(alarm, today), alarm))
            tomorrow_items.append((self._build_alarm_datetime_kst(alarm, tomorrow), alarm))

        previous_candidates = [(dt, alarm) for dt, alarm in today_items if dt <= now]
        next_candidates = [(dt, alarm) for dt, alarm in today_items if dt > now]

        previous_alarm_res = None
        next_alarm_res = None
        remaining_text = "예정된 다음 알림이 없습니다."

        if previous_candidates:
            prev_dt, prev_alarm = previous_candidates[-1]

            latest_history = (
                await AlarmHistory.filter(
                    alarm=prev_alarm,
                    sent_at__lte=now.astimezone(ZoneInfo("UTC")),
                )
                .order_by("-sent_at")
                .first()
            )
            is_confirmed = latest_history.is_confirmed if latest_history else False

            previous_alarm_res = DashboardAlarmItemResponse(
                time=self._normalize_alarm_time(prev_alarm.alarm_time).strftime("%H:%M"),
                label=self._get_dashboard_alarm_label(prev_alarm),
                is_confirmed=is_confirmed,
            )

        if next_candidates:
            next_dt, next_alarm = next_candidates[0]
        else:
            next_dt, next_alarm = tomorrow_items[0]

        next_alarm_res = DashboardAlarmItemResponse(
            time=self._normalize_alarm_time(next_alarm.alarm_time).strftime("%H:%M"),
            label=self._get_dashboard_alarm_label(next_alarm),
            is_confirmed=False,
        )
        remaining_text = self._format_remaining_text(next_dt, now)

        return DashboardAlarmSummaryResponse(
            previous_alarm=previous_alarm_res,
            next_alarm=next_alarm_res,
            remaining_text=remaining_text,
        )

    def _build_history_title_body(self, alarm: Alarm) -> tuple[str, str]:
        med_name = alarm.current_med.medication_name if alarm.current_med else None

        if alarm.alarm_type == "MED":
            return "복약 알람", f"{med_name or '약'} 복용 시간입니다."
        if alarm.alarm_type == "BP_MORNING":
            return "혈압 알람", "아침 혈압 측정 시간입니다."
        if alarm.alarm_type == "BP_EVENING":
            return "혈압 알람", "저녁 혈압 측정 시간입니다."
        if alarm.alarm_type == "BS_FASTING":
            return "혈당 알람", "아침 공복 혈당 측정 시간입니다."
        if alarm.alarm_type == "BS_POSTMEAL":
            return "혈당 알람", "식후 2시간 혈당 측정 시간입니다."
        if alarm.alarm_type == "BS_BEDTIME":
            return "혈당 알람", "취침 전 혈당 측정 시간입니다."
        return "알람", "알람 시간이 되었습니다."

    def _to_history_response(self, history: AlarmHistory) -> AlarmHistoryResponse:
        alarm = history.alarm
        title, body = self._build_history_title_body(alarm)

        sent_at_kst = history.sent_at_kst.isoformat() if history.sent_at else ""

        return AlarmHistoryResponse(
            history_id=history.id,
            alarm_id=alarm.id,
            alarm_type=alarm.alarm_type,
            title=title,
            body=body,
            sent_at=sent_at_kst,
            is_confirmed=history.is_confirmed,
        )

    async def _trim_user_alarm_histories(self, user: User) -> None:
        keep_ids = (
            await AlarmHistory.filter(alarm__user=user)
            .order_by("-sent_at")
            .limit(self.HISTORY_KEEP_LIMIT)
            .values_list("id", flat=True)
        )

        if not keep_ids:
            return

        await AlarmHistory.filter(alarm__user=user).exclude(id__in=list(keep_ids)).delete()

    async def get_user_alarm_histories(self, user: User, limit: int = 15) -> list[AlarmHistoryResponse]:
        histories = (
            await AlarmHistory.filter(alarm__user=user)
            .prefetch_related("alarm__current_med")
            .order_by("-sent_at")
            .limit(limit)
        )
        return [self._to_history_response(history) for history in histories]

    async def confirm_alarm_history(self, user: User, history_id: int) -> None:
        history = await AlarmHistory.filter(id=history_id, alarm__user=user).prefetch_related("alarm").first()

        if not history:
            raise ValueError("알람 이력을 찾을 수 없습니다.")

        history.is_confirmed = True
        history.read_at = history.read_at or datetime.now(tz=ZoneInfo("UTC"))
        history.snoozed_until = None
        await history.save()

        await self._trim_user_alarm_histories(user)

    async def snooze_alarm_history(self, user: User, history_id: int, minutes: int = 10) -> None:
        history = await AlarmHistory.filter(id=history_id, alarm__user=user).prefetch_related("alarm").first()

        if not history:
            raise ValueError("알람 이력을 찾을 수 없습니다.")

        if history.is_confirmed:
            raise ValueError("이미 확인된 알람은 미룰 수 없습니다.")

        if (history.snooze_count or 0) >= 1:
            raise ValueError("이 알람은 이미 한 번 미뤄졌습니다.")

        now_utc = datetime.now(tz=ZoneInfo("UTC"))
        history.snoozed_until = now_utc + timedelta(minutes=minutes)
        history.snooze_count = 1
        await history.save()

        await self._trim_user_alarm_histories(user)
