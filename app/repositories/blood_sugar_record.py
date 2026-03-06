from typing import cast

from app.models.blood_sugar_record import BloodSugarRecord


class BloodSugarRecordRepository:
    """
    User 모델에 대한 데이터베이스 접근 및 CRUD 연산을 담당하는 레포지토리 클래스입니다.
    """

    def __init__(self):
        self._model = BloodSugarRecord

    # 사용자에 해당하는 혈당 기록 목록 가져오기
    async def get_by_user_id(self, user_id: str) -> list[BloodSugarRecord]:
        """
        사용자 아이디를 이용해 혈당 기록을 조회합니다.

        Args:
            user_id (str): 조회할 사용자 아이디

        Returns:
            list[BloodSugarRecord]: 혈당 기록 리스트
        """
        return cast(list[BloodSugarRecord], await self._model.filter(user_id=user_id).order_by("-created_at").limit(30))

    async def create_blood_sugar(self, data: dict):
        return await self._model.create(**data)
