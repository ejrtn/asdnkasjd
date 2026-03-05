from app.dtos.health import BloodPressureRequest, BloodSugarRequest, FullHealthProfileSaveRequest
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
        user_id = user.id if user else None

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

    async def blood_sugar_save(self, blood_sugar: BloodSugarRequest, user_id: str):
        # Pydantic → dict 변환
        data = blood_sugar.model_dump()
        data["user_id"] = user_id

        await self.blood_sugar_record_repo.create_blood_sugar(data)

    async def blood_pressure_save(self, blood_pressure: BloodPressureRequest, user_id: str):
        # Pydantic → dict 변환
        data = blood_pressure.model_dump()
        data["user_id"] = user_id

        await self.blood_pressure_record_repo.create_blood_pressure(data)

    async def save_full_health_profile(self, user_id: str, request: FullHealthProfileSaveRequest):
        """
        전체 건강 프로필 정보를 통합하여 저장합니다.
        기존의 알러지, 기저질환, 복용 약물 정보를 삭제하고 새로 전달받은 정보로 교체합니다.
        """
        # 1. 건강 프로필 기본 정보 (신장, 체중 등) 업데이트 또는 생성
        profile_data = {
            "family_history": request.family_history,
            "family_history_note": request.family_history_note,
            "height_cm": request.height_cm,
            "weight_kg": request.weight_kg,
            "weight_change": request.weight_change,
            "sleep_hours": request.sleep_hours,
            "sleep_change": request.sleep_change,
            "smoking_status": request.smoking_status,
            "smoking_years": request.smoking_years,
            "smoking_per_week": request.smoking_per_week,
            "drinking_status": request.drinking_status,
            "exercise_frequency": request.exercise_frequency,
            "diet_type": request.diet_type,
        }
        await self.health_profile_repo.update_or_create(user_id, profile_data)

        # 2. 알러지 정보 교체
        await self.allergy_repo.delete_by_user_id(user_id)
        if request.allergies:
            await self.allergy_repo.create_many(user_id, [a.model_dump() for a in request.allergies])

        # 3. 만성질환 정보 교체
        await self.chronic_disease_repo.delete_by_user_id(user_id)
        if request.chronic_diseases:
            # DTO 필드명(name, when_to_diagnose)을 모델 필드명(disease_name, when_to_diagnose)으로 매핑
            cd_data = [
                {"disease_name": cd.name, "when_to_diagnose": cd.when_to_diagnose} for cd in request.chronic_diseases
            ]
            await self.chronic_disease_repo.create_many(user_id, cd_data)

        # 4. 복용 약물 정보 교체
        await self.current_med_repo.delete_by_user_id(user_id)
        if request.medications:
            await self.current_med_repo.create_many(user_id, [m.model_dump() for m in request.medications])

        return {"status": "success", "detail": "건강 정보가 성공적으로 저장되었습니다."}
