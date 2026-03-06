from typing import Any, cast

from app.models.user import User
from app.repositories.blood_sugar_record import BloodSugarRecordRepository


class BloodSugarRecordService:
    """
    사용자 건강 프로필(정적/준정적 정보)을 담당하는 서비스 클래스입니다.
    """

    def __init__(self):
        self.blood_sugar_record_repo = BloodSugarRecordRepository()

    async def generate_blood_sugar(self, user: User | None = None) -> list[dict[str, Any]]:
        """
        사용자 건강 프로필(정적/준정적 정보)을 조회하여 반환합니다.
        사용자가 로그인하지 않은 경우 데모 계정 정보를 반환합니다.

        Args:
            user (User | None): 사용자 객체

        Returns:
            dict: 통합 건강 프로필 정보
        """
        user_id = user.id if user else None

        return cast(list[dict[str, Any]], await self.blood_sugar_record_repo.get_by_user_id(user_id))
