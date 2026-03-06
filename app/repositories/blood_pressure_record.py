from typing import cast

from app.models.blood_pressure_record import BloodPressureRecord


class BloodPressureRecordRepository:
    """
    BloodPressureRecord 모델에 대한 데이터베이스 접근 및 CRUD 연산을 담당하는 레포지토리 클래스입니다.
    """

    def __init__(self):
        self._model = BloodPressureRecord

    async def get_by_user_id(self, user_id: str) -> list[BloodPressureRecord]:
        """
        사용자 아이디를 이용해 혈압 기록 목록을 조회합니다.
        """
        return cast(
            list[BloodPressureRecord], await self._model.filter(user_id=user_id).order_by("-created_at").limit(30)
        )

    async def create_blood_pressure(self, data: dict):
        return await self._model.create(**data)
