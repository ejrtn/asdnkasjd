from typing import cast

from app.models.current_med import CurrentMed


class CurrentMedRepository:
    """
    User 모델에 대한 데이터베이스 접근 및 CRUD 연산을 담당하는 레포지토리 클래스입니다.
    """

    def __init__(self):
        self._model = CurrentMed

    # 사용자에 해당하는 현재 복용 약물 목록 가져오기
    async def get_by_user_id(self, user_id: str) -> list[CurrentMed]:
        """
        사용자 아이디를 이용해 현재 복용 약물을 조회합니다.

        Args:
            user_id (str): 조회할 사용자 아이디

        Returns:
            list[CurrentMed]: 현재 복용 약물 리스트
        """
        return cast(list[CurrentMed], await self._model.filter(user_id=user_id).all())
