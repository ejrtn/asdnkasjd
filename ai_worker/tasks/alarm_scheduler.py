"""
알람 스케줄러 태스크
1분마다 현재 시간과 일치하는 활성 알람을 체크하여 FCM 푸시 발송
"""

import asyncio
import logging
import zoneinfo
from datetime import datetime

from ai_worker.core.config import Config
from ai_worker.tasks.fcm import send_push_notification

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


async def check_and_send_alarms() -> None:
    """현재 시간과 일치하는 알람을 찾아 FCM 발송 및 alarm_history 생성"""
    from app.models.alarm import Alarm
    from app.models.alarm_history import AlarmHistory

    now = datetime.now(tz=zoneinfo.ZoneInfo("Asia/Seoul"))
    current_time = now.strftime("%H:%M")

    alarms = await Alarm.filter(is_active=True).prefetch_related("user", "current_med")

    for alarm in alarms:
        alarm_time_str = (
            alarm.alarm_time.strftime("%H:%M") if hasattr(alarm.alarm_time, "strftime") else str(alarm.alarm_time)[:5]
        )

        if alarm_time_str != current_time:
            continue

        # alarm_history 생성
        await AlarmHistory.create(alarm=alarm, is_confirmed=False)

        # FCM 토큰이 있으면 푸시 발송
        user = alarm.user
        if not user.fcm_token or not user.alarm_tf:
            continue

        alarm_type = alarm.alarm_type
        title = ALARM_LABELS.get(alarm_type, "알람")
        body = ALARM_BODIES.get(alarm_type, "알람 시간입니다.")

        if alarm_type == "MED" and alarm.current_med:
            body = f"{alarm.current_med.medication_name} 복용 시간입니다."

        await send_push_notification(
            fcm_token=user.fcm_token,
            title=title,
            body=body,
            data={"alarm_id": str(alarm.id), "alarm_type": alarm_type},
        )
        logging.info(f"📱 알람 발송: user={user.id}, type={alarm_type}, time={current_time}")


async def run_alarm_scheduler() -> None:
    """정각에 맞춰 알람 체크 루프"""
    logging.info("⏰ 알람 스케줄러 루프 시작")

    # 첫 번째 정각까지 대기
    now = datetime.now(tz=zoneinfo.ZoneInfo("Asia/Seoul"))
    seconds_until_next_minute = 60 - now.second
    logging.info(f"⏱️ 다음 정각까지 {seconds_until_next_minute}초 대기")
    await asyncio.sleep(seconds_until_next_minute)

    while True:
        try:
            logging.info("⏳ 알람 체크 중...")
            await check_and_send_alarms()
            logging.info("✅ 알람 체크 완료, 60초 대기")
        except Exception as e:
            logging.error(f"❌ 알람 스케줄러 오류: {e}")
        await asyncio.sleep(60)
