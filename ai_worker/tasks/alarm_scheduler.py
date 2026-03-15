"""
알람 스케줄러 태스크
1분마다 현재 시간과 일치하는 활성 알람을 체크하여 FCM 푸시 발송
"""

import asyncio
import logging
import zoneinfo
from datetime import datetime, time, timedelta

from ai_worker.core.config import Config
from ai_worker.tasks.fcm import send_push_notification
from app.models.user import User
from app.services.alarm import AlarmService
from app.services.plan_check_list import PlanCheckListService

config = Config()

ALARM_LABELS = {
    "MED": "복약 알람",
    "BP_MORNING": "혈압 측정 알람 (아침)",
    "BP_EVENING": "혈압 측정 알람 (저녁)",
    "BS_FASTING": "혈당 측정 알람 (공복)",
    "BS_POSTMEAL": "혈당 측정 알람 (식후 2시간)",
    "BS_BEDTIME": "혈당 측정 알람 (취침 전)",
}

ALARM_BODIES = {
    "MED": "약 복용 시간입니다. 잊지 말고 복용하세요!",
    "BP_MORNING": "기상 후 1시간 내 혈압을 측정해주세요.",
    "BP_EVENING": "잠들기 전 혈압을 측정해주세요.",
    "BS_FASTING": "공복 혈당을 측정할 시간입니다.",
    "BS_POSTMEAL": "식후 2시간 혈당을 측정해주세요.",
    "BS_BEDTIME": "취침 전 혈당을 측정해주세요.",
}


def normalize_alarm_time(value: object) -> str:
    """alarm_time 값을 HH:MM 형식으로 통일"""
    if isinstance(value, time):
        return value.strftime("%H:%M")

    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours = (total_seconds // 3600) % 24
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"

    if hasattr(value, "strftime"):
        return str(value.strftime("%H:%M"))  # type: ignore[union-attr]

    text = str(value).strip()

    if ":" in text:
        parts = text.split(":")
        if len(parts) >= 2:
            try:
                hours = int(parts[0])
                minutes = int(parts[1])
                return f"{hours:02d}:{minutes:02d}"
            except ValueError:
                pass
    return text[:5]


def is_alarm_due_within_last_minute(alarm_time_value: object, now: datetime) -> bool:
    alarm_hhmm = normalize_alarm_time(alarm_time_value)
    try:
        hour, minute = map(int, alarm_hhmm.split(":"))
    except ValueError:
        return False

    alarm_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    diff = (now - alarm_dt).total_seconds()

    # 자정 무렵 예외처리 (예: 현재 00:00:10 인데 알람이 23:59인 경우)
    if diff < -86000:
        diff += 86400

    return 0 <= diff < 60


async def check_and_send_alarms() -> None:
    """현재 시간과 일치하는 알람을 찾아 FCM 발송 및 alarm_history 생성"""
    import os

    from app.models.alarm import Alarm
    from app.models.alarm_history import AlarmHistory

    now = datetime.now(tz=zoneinfo.ZoneInfo("Asia/Seoul"))
    current_time = now.strftime("%H:%M")

    logging.info(f"[SCHEDULER] tick now={now.isoformat()} current_time={current_time}")
    logging.info(f"[SCHEDULER] DB_URL={os.getenv('DATABASE_URL')}")

    alarms = await Alarm.filter(is_active=True).prefetch_related("user", "current_med")
    logging.info(f"[SCHEDULER] active alarms count={len(alarms)}")

    service = AlarmService()
    today = now.date()

    for alarm in alarms:
        if not service._matches_repeat_day(alarm, today):
            continue

        alarm_time_str = normalize_alarm_time(alarm.alarm_time)

        logging.info(
            f"[SCHEDULER] checking alarm_id={alarm.id} type={alarm.alarm_type} "
            f"time={alarm_time_str} user_id={alarm.user.id}"
        )

        if not is_alarm_due_within_last_minute(alarm.alarm_time, now):
            continue

        alarm_hhmm = normalize_alarm_time(alarm.alarm_time)
        alarm_target_dt = now.replace(
            hour=int(alarm_hhmm.split(":")[0]),
            minute=int(alarm_hhmm.split(":")[1]),
            second=0,
            microsecond=0,
        )
        latency = (now - alarm_target_dt).total_seconds()

        logging.info(
            f"[SCHEDULER] MATCHED alarm_id={alarm.id} type={alarm.alarm_type} "
            f"time={alarm_time_str} latency={latency:.2f}s"
        )

        existing_recent_history = await AlarmHistory.filter(
            alarm=alarm,
            sent_at__gte=now.astimezone(zoneinfo.ZoneInfo("UTC")) - timedelta(minutes=2),
        ).first()

        if existing_recent_history:
            logging.info(
                f"[SCHEDULER] skip duplicate alarm_id={alarm.id} recent_history_id={existing_recent_history.id}"
            )
            continue

        try:
            history = await AlarmHistory.create(
                alarm=alarm,
                is_confirmed=False,
                snooze_count=0,
            )

            await service._trim_user_alarm_histories(alarm.user)

            logging.info(
                f"[SCHEDULER] history created history_id={history.id} alarm_id={alarm.id} sent_at={history.sent_at}"
            )
        except Exception as e:
            logging.exception(f"[SCHEDULER] history create failed alarm_id={alarm.id}: {e}")
            continue

        user = alarm.user
        if not user.fcm_token or not user.alarm_tf:
            logging.info(
                f"[SCHEDULER] skip push user_id={user.id} has_token={bool(user.fcm_token)} alarm_tf={user.alarm_tf}"
            )
            continue

        alarm_type = alarm.alarm_type
        title = ALARM_LABELS.get(alarm_type, "알람")
        body = ALARM_BODIES.get(alarm_type, "알람 시간입니다.")

        if alarm_type == "MED" and alarm.current_med:
            body = f"{alarm.current_med.medication_name} 복용 시간입니다."

        try:
            await send_push_notification(
                fcm_token=user.fcm_token,
                title=title,
                body=body,
                data={
                    "alarm_id": str(alarm.id),
                    "alarm_type": alarm_type,
                    "history_id": str(history.id),
                },
            )
            logging.info(f"[SCHEDULER] push sent user={user.id} type={alarm_type} time={current_time}")
        except Exception as e:
            logging.exception(f"[SCHEDULER] push failed alarm_id={alarm.id}: {e}")


async def check_and_send_snoozed_alarm_histories() -> None:
    from app.models.alarm_history import AlarmHistory

    now_utc = datetime.now(tz=zoneinfo.ZoneInfo("UTC"))

    histories = await AlarmHistory.filter(
        is_confirmed=False,
        snoozed_until__lte=now_utc,
        snooze_count=0,
    ).prefetch_related("alarm__user", "alarm__current_med")

    for history in histories:
        alarm = history.alarm
        user = alarm.user if alarm else None
        if not alarm or not user:
            continue

        if not user.fcm_token or not user.alarm_tf:
            continue

        alarm_type = alarm.alarm_type
        title = ALARM_LABELS.get(alarm_type, "알람")
        body = ALARM_BODIES.get(alarm_type, "알람 시간입니다.")

        if alarm_type == "MED" and alarm.current_med:
            body = f"{alarm.current_med.medication_name} 복용 시간입니다."

        try:
            await send_push_notification(
                fcm_token=user.fcm_token,
                title=title,
                body=body,
                data={
                    "alarm_id": str(alarm.id),
                    "alarm_type": alarm_type,
                    "history_id": str(history.id),
                    "snooze_count": "1",
                },
            )

            history.snooze_count = 1
            history.snoozed_until = None
            await history.save(update_fields=["snooze_count", "snoozed_until"])

            logging.info(f"[SCHEDULER] snoozed push sent history_id={history.id} alarm_id={alarm.id}")
        except Exception as e:
            logging.exception(f"[SCHEDULER] snoozed push failed history_id={history.id}: {e}")


async def sync_all_users_daily_plans() -> None:
    """모든 사용자의 일일 실행 플랜을 동기화 (자정 실행)"""
    logging.info("[SCHEDULER] Starting daily plan sync for all users")
    service = PlanCheckListService()

    users = await User.all()

    for user in users:
        try:
            await service.sync_automated_plans(user.id)
            logging.info(f"[SCHEDULER] Synced plans for user_id={user.id}")
        except Exception as e:
            logging.error(f"[SCHEDULER] Failed to sync plans for user_id={user.id}: {e}")

    logging.info("[SCHEDULER] Completed daily plan sync")


async def run_alarm_scheduler() -> None:
    """매 분 경계에 맞춰 알람 체크 루프"""
    logging.info("⏰ 알람 스케줄러 루프 시작")

    tz = zoneinfo.ZoneInfo("Asia/Seoul")

    while True:
        try:
            now = datetime.now(tz=tz)

            # 현재 분 기준 체크
            logging.info(f"⏳ 알람 체크 중... now={now.isoformat()}")
            await check_and_send_alarms()
            await check_and_send_snoozed_alarm_histories()

            now_after = datetime.now(tz=tz)
            if now_after.hour == 0 and now_after.minute == 0:
                await sync_all_users_daily_plans()

        except Exception as e:
            logging.exception(f"❌ 알람 스케줄러 오류: {e}")

        # 다음 체크 시점 계산 (20초 단위 정렬: 00, 20, 40초)
        now = datetime.now(tz=tz)
        current_second = now.second + (now.microsecond / 1_000_000)

        # 20초 단위로 올림 (0->20, 20->40, 40->60)
        next_boundary = ((int(current_second) // 20) + 1) * 20
        seconds_until_next = next_boundary - current_second

        if seconds_until_next <= 0:
            seconds_until_next = 0.1

        logging.info(f"✅ 알람 체크 완료, 다음 체크까지 {seconds_until_next:.2f}초 대기 (목표: {next_boundary}초 지점)")
        await asyncio.sleep(seconds_until_next)
