from typing import cast

from app.models.llm_life_guide import LLMLifeGuide


class LLMLifeGuideRepository:
    """
    User 모델에 대한 데이터베이스 접근 및 CRUD 연산을 담당하는 레포지토리 클래스입니다.
    """

    def __init__(self):
        self._model = LLMLifeGuide

    # 사용자에 해당하는 질병 가져오기
    async def get_by_user_id(self, user_id: str) -> LLMLifeGuide | None:
        """
        사용자 아이디를 이용해 알러지를 조회합니다.

        Args:
            user_id (str): 조회할 사용자 아이디

        Returns:
            HealthProfile | None: 사용자 객체 또는 없음
        """
        llm_life_guide: LLMLifeGuide | None = await self._model.filter(user_id=user_id).first()
        return llm_life_guide

    async def update_or_create(self, user_id: str, data: dict) -> LLMLifeGuide:
        """
        사용자 아이디를 이용해 건강 프로필을 업데이트하거나 생성합니다.
        """

        llm_life_guide, created = await self._model.update_or_create(user_id=user_id, defaults=data)

        return cast(LLMLifeGuide, llm_life_guide)
