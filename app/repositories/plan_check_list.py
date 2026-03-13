from typing import cast

from app.models.plan_check_list import PlanCheckList


class PlanCheckListRepository:
    """
    User 모델에 대한 데이터베이스 접근 및 CRUD 연산을 담당하는 레포지토리 클래스입니다.
    """

    def __init__(self):
        self._model = PlanCheckList

    async def create(self, data: dict) -> PlanCheckList:
        return cast(PlanCheckList, await self._model.create(**data))

    async def delete_by_id(self, user_id: str, id: int):
        """
        사용자 아이디와 레코드 아이디가 일치하는 혈압 기록을 삭제합니다.
        """
        await self._model.filter(user_id=user_id, id=id).delete()

    async def get_all_by_user_id(self, user_id: str):
        """
        사용자 아이디에 해당하는 모든 계획 항목을 조회합니다.
        """
        return await self._model.filter(user_id=user_id).all()

    async def toggle_completed(self, user_id: str, id: int) -> PlanCheckList:
        """
        계획 항목의 완료 상태를 토글합니다.
        """
        item = cast(PlanCheckList, await self._model.get(user_id=user_id, id=id))
        item.is_completed = not item.is_completed
        await item.save()
        return item

    async def reset_all_by_user_id(self, user_id: str):
        """
        사용자의 모든 계획 항목을 미완료 상태로 초기화합니다.
        """
        await self._model.filter(user_id=user_id).update(is_completed=False)

    async def delete_all_by_user_id(self, user_id: str):
        """
        사용자의 모든 계획 항목을 삭제합니다.
        """
        await self._model.filter(user_id=user_id).delete()

    async def delete_all_by_type(self, user_id: str, plan_type: str):
        """
        사용자의 특정 타입 계획 항목을 삭제합니다.
        """
        await self._model.filter(user_id=user_id, plan_type=plan_type).delete()

    async def exists_by_content(self, user_id: str, content: str) -> bool:
        """
        동일한 내용의 계획 항목이 존재하는지 확인합니다.
        """
        return cast(bool, await self._model.filter(user_id=user_id, content=content).exists())

    async def exists_by_content_and_type(self, user_id: str, content: str, plan_type: str) -> bool:
        """
        동일한 내용과 타입을 가진 계획 항목이 존재하는지 확인합니다.
        """
        return cast(bool, await self._model.filter(user_id=user_id, content=content, plan_type=plan_type).exists())
