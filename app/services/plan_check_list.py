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
        현재 설정된 모든 활성 알람 정보를 바탕으로 오늘의 체크리스트를 동기화합니다.
        """
        # 1. 기존 'pill' 타입 항목 삭제 (알람 기반 항목들)
        await self._repo.delete_all_by_type(user_id, plan_type="pill")

        # 2. 활성화된 모든 알람 조회
        alarms = await Alarm.filter(user_id=user_id, is_active=True).prefetch_related("current_med")

        # 알람 타입별 한글 명칭 매핑
        type_map = {
            "MED": "복약",
            "BP_MORNING": "혈압 아침 측정",
            "BP_EVENING": "혈압 저녁 측정",
            "BS_FASTING": "혈당 공복 측정",
            "BS_POSTMEAL": "혈당 식후 측정",
            "BS_BEDTIME": "혈당 취침 전 측정",
        }

        for alarm in alarms:
            time_str = self._format_time(alarm.alarm_time)

            if alarm.alarm_type == "MED" and alarm.current_med:
                content = f"[{time_str}] {alarm.current_med.medication_name} 복약 알람"
            else:
                alarm_name = type_map.get(alarm.alarm_type, "측정")
                content = f"[{time_str}] {alarm_name} 알람"

            # 이미 존재하는지 확인 (중복 방지)
            if not await self._repo.exists_by_content_and_type(user_id, content, "pill"):
                await self._repo.create({"user_id": user_id, "content": content, "plan_type": "pill"})

    async def sync_llm_plans(self, user_id: str):
        """
        AI(LLM)를 통해 맞춤형 건강 관리 플랜을 생성하고 체크리스트에 저장합니다.
        """
        from app.services.health_profile import HealthProfileService

        hp_service = HealthProfileService()
        recommendation_result = await hp_service.health_profile_recommend_plan(user_id)

        if recommendation_result and "content" in recommendation_result:
            # 기존 'llm' 타입 항목 삭제
            await self._repo.delete_all_by_type(user_id, plan_type="llm")

            checklist = recommendation_result["content"].get("checklist", [])
            for content in checklist:
                await self._repo.create({"user_id": user_id, "content": content, "plan_type": "llm"})

    async def sync_automated_plans(self, user_id: str):
        """
        매일 자정에 실행되거나 추천이 필요할 때 자동 플랜들을 동기화합니다.
        """
        # 1. 초기화 (매일 체크해야 하므로 완료 상태만 리셋)
        await self._repo.reset_all_by_user_id(user_id)

        # 2. 복약을 위한 플랜 동기화
        await self.sync_pill_plans(user_id)
