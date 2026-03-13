from datetime import time, timedelta
from typing import cast

from app.dtos.plan_check_list import PlanCheckListRequest
from app.models.alarm import Alarm
from app.models.plan_check_list import PlanCheckList
from app.repositories.plan_check_list import PlanCheckListRepository


class PlanCheckListService:
    def __init__(self):
        self._repo = PlanCheckListRepository()

    async def create(self, user_id: str, data: PlanCheckListRequest) -> PlanCheckList:
        data_dict = data.model_dump()
        data_dict["user_id"] = user_id
        return cast(PlanCheckList, await self._repo.create(data=data_dict))

    async def delete_by_id(self, user_id: str, id: int):
        await self._repo.delete_by_id(user_id=user_id, id=id)

    async def delete_all_by_user(self, user_id: str):
        await self._repo.delete_all_by_user_id(user_id=user_id)

    async def delete_all_by_type(self, user_id: str, plan_type: str):
        await self._repo.delete_all_by_type(user_id=user_id, plan_type=plan_type)

    async def get_all_by_user(self, user_id: str):
        return await self._repo.get_all_by_user_id(user_id=user_id)

    async def toggle_completed(self, user_id: str, id: int):
        return await self._repo.toggle_completed(user_id=user_id, id=id)

    def _format_time(self, t: object) -> str:
        """time 또는 timedelta 객체를 HH:MM 형식의 문자열로 변환합니다."""
        if isinstance(t, time):
            return cast(str, t.strftime("%H:%M"))
        if isinstance(t, timedelta):
            total_seconds = int(t.total_seconds())
            hours = (total_seconds // 3600) % 24
            minutes = (total_seconds % 3600) // 60
            return f"{hours:02d}:{minutes:02d}"
        return str(t)

    async def sync_pill_plans(self, user_id: str):
        """
        현재 복용 중인 약물과 알람 정보를 바탕으로 오늘의 복약 체크리스트를 동기화합니다.
        """
        # 1. 기존 'pill' 타입 항목만 삭제 (새로 동기화하므로)
        await self._repo.delete_all_by_type(user_id, plan_type="pill")

        # 2. 활성화된 복약 알람 조회 (current_med가 있는 경우)
        alarms = await Alarm.filter(user_id=user_id, alarm_type="MED", is_active=True).prefetch_related("current_med")

        for alarm in alarms:
            if alarm.current_med:
                # 사용자가 요청한 형식: [약이름] [HH:mm] 알람 설정
                time_str = self._format_time(alarm.alarm_time)
                content = f"{alarm.current_med.medication_name} {time_str} 알람 설정"
                # 이미 존재하는지 확인 (중복 방지)
                if not await self._repo.exists_by_content_and_type(user_id, content, "pill"):
                    await self._repo.create({"user_id": user_id, "content": content, "plan_type": "pill"})

    async def sync_automated_plans(self, user_id: str):
        """
        매일 자정에 실행되거나 추천이 필요할 때 자동 플랜들을 동기화합니다.
        """
        # 1. 초기화 (매일 체크해야 하므로 완료 상태만 리셋)
        await self._repo.reset_all_by_user_id(user_id)

        # 2. 복약을 위한 플랜 동기화
        await self.sync_pill_plans(user_id)
