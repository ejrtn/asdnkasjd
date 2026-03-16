from datetime import datetime

from tortoise.expressions import Q

from app.models.alarm import Alarm
from app.models.alarm_history import AlarmHistory


class AlarmRepository:
    """
    User 모델에 대한 데이터베이스 접근 및 CRUD 연산을 담당하는 레포지토리 클래스입니다.
    """

    def __init__(self):
        self._model = Alarm

    # 사용자에 해당하는 알림 가져오기
    async def get_by_user_id(self, user_id: str) -> Alarm | None:
        """
        사용자 아이디를 이용해 알림을 조회합니다.
        Args:
            user_id (str): 조회할 사용자 아이디

        Returns:
            Alarm | None: 사용자 객체 또는 없음
        """
        alarm: Alarm | None = await self._model.get_or_none(user_id=user_id)  # type: ignore[assignment]
        return alarm

    async def get_active_alarms_by_user_id(self, user_id: str) -> list[Alarm]:
        """활성화된 알람 목록 조회 (current_med 포함)"""
        alarms: list[Alarm] = (
            await self._model.filter(user_id=user_id, is_active=True).prefetch_related("current_med").all()
        )
        return alarms


class AlarmHistoryRepository:
    def __init__(self):
        self._model = AlarmHistory

    async def get_today_histories_by_user_id(self, user_id: str, today: datetime) -> list[AlarmHistory]:
        """오늘 날짜의 알람 히스토리 조회 (alarm, alarm.current_med 포함)"""
        start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end = today.replace(hour=23, minute=59, second=59, microsecond=999999)

        histories: list[AlarmHistory] = (
            await self._model.filter(
                Q(alarm__user_id=user_id),
                Q(sent_at__gte=start),
                Q(sent_at__lte=end),
            )
            .prefetch_related("alarm", "alarm__current_med")
            .order_by("sent_at")
            .all()
        )
        return histories
