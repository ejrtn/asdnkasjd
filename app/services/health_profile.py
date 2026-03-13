from app.dtos.health import BloodPressureRequest, BloodSugarRequest, FullHealthProfileSaveRequest
from app.dtos.plan_check_list import PlanCheckListRequest
from app.models.allergy import Allergy
from app.models.blood_pressure_record import BloodPressureRecord
from app.models.blood_sugar_record import BloodSugarRecord
from app.models.chronic_disease import ChronicDisease
from app.models.current_med import CurrentMed
from app.models.health_profile import HealthProfile
from app.models.user import User
from app.rag.rag_pipeline import generate_rag_context
from app.repositories.allergy import AllergyRepository
from app.repositories.blood_pressure_record import BloodPressureRecordRepository
from app.repositories.blood_sugar_record import BloodSugarRecordRepository
from app.repositories.chronic_disease import ChronicDiseaseRepository
from app.repositories.current_med import CurrentMedRepository
from app.repositories.health_profile import HealthProfileRepository
from app.services.guide import GuideService
from app.services.llm_service import LLMService
from app.services.plan_check_list import PlanCheckListService


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
        self.guide_service = GuideService()
        self.plan_check_list = PlanCheckListService()
        self.llm_service = LLMService()

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

    async def blood_sugar(self, blood_sugar: BloodSugarRequest, user_id: str):
        # Pydantic → dict 변환
        data = blood_sugar.model_dump()
        data["user_id"] = user_id

        await self.blood_sugar_record_repo.create_blood_sugar(data)

    async def blood_pressure(self, blood_pressure: BloodPressureRequest, user_id: str):
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
            "drinking_years": request.drinking_years,
            "drinking_per_week": request.drinking_per_week,
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

        # 5. 추천 플랜 생성 및 저장 (plan_type='llm')
        recommendation_result = await self.health_profile_recommend_plan(user_id)
        if recommendation_result and "content" in recommendation_result:
            # 기존 LLM 추천 플랜만 초기화 (새로운 건강 프로필 기반 업데이트)
            await self.plan_check_list.delete_all_by_type(user_id, plan_type="llm")

            checklist = recommendation_result["content"].get("checklist", [])
            for content in checklist:
                await self.plan_check_list.create(user_id, PlanCheckListRequest(content=content, plan_type="llm"))

        # 6. 복약 알림 기반 플랜 동기화 (plan_type='pill')
        await self.plan_check_list.sync_pill_plans(user_id)

        return {"status": "success", "detail": "건강 정보가 성공적으로 저장되었습니다."}

    async def blood_sugar_delete(self, user_id: str, record_id: int):
        """혈당 기록을 삭제합니다."""
        await self.blood_sugar_record_repo.delete_by_id(user_id, record_id)
        return {"status": "success", "detail": "혈당 기록이 삭제되었습니다."}

    async def blood_pressure_delete(self, user_id: str, record_id: int):
        """혈압 기록을 삭제합니다."""
        await self.blood_pressure_record_repo.delete_by_id(user_id, record_id)
        return {"status": "success", "detail": "혈압 기록이 삭제되었습니다."}

    async def health_profile_recommend_plan(self, user_id: str):
        # API 키가 없으면 더미 데이터 반환
        if not self.llm_service.client:
            return self._get_dummy_guide()

        # 1. 실제 사용자 데이터 조회
        health_data = await self._fetch_user_health_data(user_id)
        lifestyle = self._extract_lifestyle(health_data["profile"])

        # 2. RAG context 생성
        rag_context = await self._generate_rag_context_str(health_data["disease_list"], lifestyle)

        # 3. Prompt 구성 및 LLM 생성
        prompt = self._build_guide_prompt(health_data, lifestyle, rag_context)

        try:
            content_json = await self.llm_service.generate_json(
                messages=[
                    {
                        "role": "system",
                        "content": "의사로서 정확한 답변을 해야한다. JSON 형식으로만 답변한다.",
                    },
                    {"role": "user", "content": prompt},
                ],
                model="gpt-4o-mini",
                temperature=0.4,
            )

            return {
                "content": content_json,
                "activity": False,
            }

        except Exception as e:
            return await self._handle_generation_error(user_id, e)

    async def _fetch_user_health_data(self, user_id: str | None) -> dict:
        try:
            diseases = await ChronicDisease.filter(user_id=user_id).all()
            allergies = await Allergy.filter(user_id=user_id).all()
            meds = await CurrentMed.filter(user_id=user_id).all()
            profile = await HealthProfile.get_or_none(user_id=user_id)

            bp_records = await BloodPressureRecord.filter(user_id=user_id).order_by("-created_at").limit(1)
            bs_records = await BloodSugarRecord.filter(user_id=user_id).order_by("-created_at").limit(1)

            return {
                "disease_list": [d.disease_name for d in diseases],
                "allergy_list": [a.allergy_name for a in allergies],
                "med_list": [m.medication_name for m in meds],
                "bp_list": [f"{r.systolic}/{r.diastolic} mmHg" for r in bp_records],
                "bs_list": [f"{r.glucose_mg_dl} mg/dL ({r.measure_type})" for r in bs_records],
                "profile": profile,
            }
        except Exception as e:
            print(f"[Fetch User Health Data Error] {e}")
            return {
                "disease_list": [],
                "allergy_list": [],
                "med_list": [],
                "bp_list": [],
                "bs_list": [],
                "profile": None,
            }

    def _extract_lifestyle(self, profile: HealthProfile | None) -> dict:
        if not profile:
            return {
                "smoking_status": "정보 없음",
                "drinking_status": "정보 없음",
                "exercise_frequency": "정보 없음",
                "diet_type": "정보 없음",
                "sleep_change": "정보 없음",
                "sleep_hours": None,
                "weight_change": "정보 없음",
            }
        return {
            "smoking_status": profile.smoking_status,
            "drinking_status": profile.drinking_status,
            "exercise_frequency": profile.exercise_frequency,
            "diet_type": profile.diet_type,
            "sleep_change": profile.sleep_change,
            "sleep_hours": profile.sleep_hours,
            "weight_change": profile.weight_change,
        }

    async def _generate_rag_context_str(self, disease_list: list[str], lifestyle: dict) -> str:
        try:
            return generate_rag_context(
                selected_diseases=disease_list,
                other_disease=None,
                lifestyle=lifestyle,
                max_queries=5,
                top_k=2,
            )
        except Exception as e:
            print(f"[RAG ERROR] {e}")
            return "[참고 문서]\n관련 참고 문서를 불러오지 못했습니다."

    def _build_guide_prompt(self, health_data: dict, lifestyle: dict, rag_context: str) -> str:
        s_hours = lifestyle.get("sleep_hours")
        s_hours_text = f"{s_hours}시간" if s_hours is not None else "정보 없음"

        return f"""
        너는 사용자의 질환, 복용 약물, 알레르기 정보를 분석하여 맞춤형 건강 관리 루틴을 생성하는 '개인 건강 가이드'이다.

        [환자 상태]
        - 만성 질환: {", ".join(health_data["disease_list"]) if health_data["disease_list"] else "없음"}
        - 알레르기: {", ".join(health_data["allergy_list"]) if health_data["allergy_list"] else "없음"}
        - 현재 복용 약: {", ".join(health_data["med_list"]) if health_data["med_list"] else "없음"}
        - 최근 혈압 기록: {", ".join(health_data["bp_list"]) if health_data["bp_list"] else "없음"}
        - 최근 혈당 기록: {", ".join(health_data["bs_list"]) if health_data["bs_list"] else "없음"}
        - 흡연 상태: {lifestyle.get("smoking_status") or "정보 없음"}
        - 음주 상태: {lifestyle.get("drinking_status") or "정보 없음"}
        - 운동 빈도: {lifestyle.get("exercise_frequency") or "정보 없음"}
        - 식습관: {lifestyle.get("diet_type") or "정보 없음"}
        - 최근 수면 변화: {lifestyle.get("sleep_change") or "정보 없음"}
        - 수면 시간: {s_hours_text}
        - 최근 체중 변화: {lifestyle.get("weight_change") or "정보 없음"}

        [참고 문서]
        {rag_context}

        [작성 가이드라인]
        1. 의학적 확언 금지: "~병입니다", "~해야만 합니다"와 같은 단정적 진단이나 강요 대신, "~해보시는 것을 추천드려요", "~이 도움이 될 수 있습니다"와 같은 권고와 추천의 어조를 사용하라.
        2. 안전 최우선: 사용자의 알레르기 성분과 현재 복용 중인 약물 간의 상호작용을 가장 먼저 분석하라. 만약 주의가 필요한 사항이 있다면 warning 필드에 반드시 포함하라.
        3. 실천 중심 플랜: '오늘의 실행 플랜'은 사용자가 완료 후 체크박스를 누를 수 있는 구체적인 행동 단위여야 한다. (예: "건강 관리하기" (X) -> "점심 식사 후 15분 산책하기" (O))
        4. 항목 수: 매일 실천할 수 있는 플랜을 정확히 5가지 생성하라.

        [응답 JSON 구조]
        {{
            "checklist": ["체크리스트 1", "체크리스트 2", "체크리스트 3", "체크리스트 4", "체크리스트 5"]
        }}
        """.strip()

    def _get_dummy_guide(self) -> dict:
        return {
            "content": {
                "checklist": [
                    "매일 30분 가벼운 산책하기",
                    "하루 2L 이상의 충분한 수분 섭취하기",
                    "정해진 시간에 규칙적으로 식사하기",
                    "충분한 수면 시간(7-8시간) 확보하기",
                    "스트레칭으로 몸의 긴장 풀어주기",
                ]
            },
            "activity": False,
        }

    async def _handle_generation_error(self, user_id: str | None, e: Exception) -> dict:
        print(f"[HealthProfile Recommendation Error] {e}")
        return self._get_dummy_guide()
