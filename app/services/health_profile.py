from app.models.user import User
from app.repositories.allergy import AllergyRepository
from app.repositories.blood_pressure_record import BloodPressureRecordRepository
from app.repositories.blood_sugar_record import BloodSugarRecordRepository
from app.repositories.chronic_disease import ChronicDiseaseRepository
from app.repositories.current_med import CurrentMedRepository
from app.repositories.health_profile import HealthProfileRepository


class HealthProfileService:
    """
    사용자 건강 프로필(정적/준정적 정보)을 담당하는 서비스 클래스입니다.
    """

    def __init__(self):
        self.allergy_repo = AllergyRepository()
        self.blood_pressure_record_repo = BloodPressureRecordRepository()
        self.blood_sugar_record_repo = BloodSugarRecordRepository()
        self.chronic_disease_repo = ChronicDiseaseRepository()
        self.current_med_repo = CurrentMedRepository()
        self.health_profile_repo = HealthProfileRepository()

    async def generate_health_profile(self, user: User | None = None) -> dict:
        """
        사용자 건강 프로필(정적/준정적 정보)을 조회하여 반환합니다.
        사용자가 로그인하지 않은 경우 데모 계정 정보를 반환합니다.

        Args:
            user (User | None): 사용자 객체

        Returns:
            dict: 통합 건강 프로필 정보
        """
        user_id = user.id

        allergies = await self.allergy_repo.get_by_user_id(user_id)
        blood_pressure_records = await self.blood_pressure_record_repo.get_by_user_id(user_id)
        blood_sugar_records = await self.blood_sugar_record_repo.get_by_user_id(user_id)
        chronic_diseases = await self.chronic_disease_repo.get_by_user_id(user_id)
        current_meds = await self.current_med_repo.get_by_user_id(user_id)
        health_profile = await self.health_profile_repo.get_by_user_id(user_id)

        return {
            "health_profile": health_profile,
            "chronic_diseases": chronic_diseases,
            "allergies": allergies,
            "current_meds": current_meds,
            "blood_pressure_records": blood_pressure_records,
            "blood_sugar_records": blood_sugar_records,
        }
