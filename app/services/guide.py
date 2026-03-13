from datetime import datetime

from app.models.allergy import Allergy
from app.models.blood_pressure_record import BloodPressureRecord
from app.models.blood_sugar_record import BloodSugarRecord
from app.models.chronic_disease import ChronicDisease
from app.models.current_med import CurrentMed
from app.models.health_profile import HealthProfile
from app.models.user import User
from app.rag.rag_pipeline import generate_rag_context
from app.services.llm_service import LLMService


class GuideService:
    def __init__(self):
        self.llm_service = LLMService()

    # ==========================================
    # 필수 1: LLM 기반 안내 가이드 생성
    # ==========================================
    async def generate_guide(self, user_id: str | None) -> dict:
        """
        [GUIDE] 맞춤 가이드 생성(RAG 핵심).
        실제 사용자의 기저질환, 알러지, 복용약을 바탕으로 OpenAI를 통해 구조화된 가이드를 생성합니다.
        (DB 연결 실패 시 기본값으로 대체)
        """
        # API 키가 없으면 더미 데이터 반환
        if not self.llm_service.client:
            return self._get_dummy_guide()

        # 1. 즉시 로딩 상태 저장 (프론트엔드 피드백용)
        await self._update_loading_state(user_id)

        # 2. 실제 사용자 데이터 조회
        health_data = await self._fetch_user_health_data(user_id)
        lifestyle = self._extract_lifestyle(health_data["profile"])

        # 3. RAG context 생성
        rag_context = await self._generate_rag_context_str(health_data["disease_list"], lifestyle)

        # 4. Prompt 구성 및 LLM 생성
        prompt = self._build_guide_prompt(health_data, lifestyle, rag_context)

        try:
            content_json = await self.llm_service.generate_json(
                messages=[
                    {
                        "role": "system",
                        "content": "너는 꼼꼼한 간호사 출신 건강 안내 도우미다. JSON 형식으로만 답변한다.",
                    },
                    {"role": "user", "content": prompt},
                ],
                model="gpt-4o-mini",
                temperature=0.4,
            )

            # 5. 질환 누락 보정 및 저장
            fixed_content = self._fix_missing_diseases(content_json, health_data["disease_list"])

            data = {"user_current_status": prompt, "generated_content": fixed_content, "activity": False}
            await self.llm_service.update_or_create(user_id=user_id, data=data)

            return {
                "user_current_status": prompt,
                "generated_content": fixed_content,
                "activity": False,
                "created_at": datetime.now(),
            }

        except Exception as e:
            return await self._handle_generation_error(user_id, e)

    def _get_dummy_guide(self) -> dict:
        return {
            "user_current_status": "API Key Missing",
            "generated_content": {
                "section1": {
                    "title": "복약 안전성 및 주의사항",
                    "status": "주의 필요",
                    "content": "API 키가 설정되지 않아 예시 데이터를 표시합니다.",
                    "general_cautions": ["권장 용량을 준수하세요."],
                },
                "section2": {
                    "title": "질환 기반 생활습관 가이드",
                    "disease_guides": [{"name": "내 기저질환", "tips": ["충분한 수분을 섭취하세요."]}],
                    "integrated_point": "균형 잡힌 생활 패턴 유지를 권장합니다.",
                },
            },
            "activity": True,
            "created_at": datetime.now(),
        }

    async def _update_loading_state(self, user_id: str | None) -> None:
        try:
            saved = await self.llm_service.get_by_user_id(user_id)
            await self.llm_service.update_or_create(
                user_id=user_id,
                data={
                    "activity": True,
                    "user_current_status": "가이드 생성 중...",
                    "generated_content": saved.generated_content if saved else {},
                },
            )
        except Exception:
            pass

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
        except Exception:
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
                k: None
                for k in [
                    "smoking_status",
                    "drinking_status",
                    "exercise_frequency",
                    "diet_type",
                    "sleep_change",
                    "sleep_hours",
                    "weight_change",
                ]
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
        신중하고 전문적인 의료 도우미로서, 아래 환자의 건강 상태를 바탕으로 '생활 안내 가이드'를 작성해줘.

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
        1. 과한 확정 진단(예: ~병입니다)은 피하고, '권장합니다', '주의가 필요합니다' 등의 조언 톤을 유지할 것.
        2. 약물 상호작용 및 알레르기 성분을 최우선으로 체크할 것.
        3. 만약 '현재 복용 약'이 없다면, Section 1의 status를 '상호작용 없음'으로 하고, content에 "현재 복용 중인 약물이 없어 상호작용 위험이 없습니다.\n건강한 상태를 잘 유지하고 계시네요!"와 같이 줄바꿈(\n)을 포함한 긍정적인 메시지를 담아줘.
        4. Section 2는 '만성 질환' 기반의 가이드로만 구성해줘. 질환이 없다면 disease_guides를 빈 배열로 둬.
        5. Section 3(오늘의 건강 관리 수칙)은 사용자의 BMI, 수면, 운동, 식습관 데이터를 바탕으로 '일반적인 건강 관리 안내'를 제공해줘. 체크리스트 형식이 아니라 카드 형태의 가이드 구조로 작성하며, 화면 배치를 위해 반드시 '운동', '식단', '수면', '흡연/음주' 등 4가지 항목(name)을 포함해서 응답해줘. (데이터가 부족해도 일반적인 권장 수칙 제공)
        6. 반드시 아래의 JSON 구조로 응답할 것.
        7. 참고 문서의 내용을 우선 반영하여 생활습관 및 복약 안내를 작성할 것.

        [응답 JSON 구조]
        {{
        "section1": {{
            "title": "복약 안전성 및 주의사항",
            "status": "상호작용 없음 | 주의 필요 | 위험 가능성",
            "content": "상태에 따른 상세 설명 문구",
            "general_cautions": ["주의사항 1", "주의사항 2"]
        }},
        "section2": {{
            "title": "질환 기반 생활습관 가이드",
            "disease_guides": [
            {{ "name": "질환명", "tips": ["가이드 1", "가이드 2"] }}
            ],
            "integrated_point": "종합 관리 포인트 문구"
        }},
        "section3": {{
            "title": "오늘의 건강 관리 수칙",
            "health_guides": [
            {{ "name": "관리 항목(예: 수면, 식단 등)", "tips": ["가이드 1", "가이드 2"] }}
            ]
        }},
        "disclaimer": "본 서비스는 의료 진단이나 처방을 제공하지 않으며, 참고용 안내입니다."
        }}
        """.strip()

    def _fix_missing_diseases(self, content_json: dict, disease_list: list[str]) -> dict:
        try:
            sec2 = content_json.get("section2") or {}
            guides = sec2.get("disease_guides") or []
            guide_names = {g.get("name") for g in guides if isinstance(g, dict)}

            for dname in disease_list:
                if dname not in guide_names:
                    guides.append(
                        {
                            "name": dname,
                            "tips": ["(추가 입력 시 더 정확한 맞춤 가이드를 제공할 수 있어요.)"],
                        }
                    )

            sec2["disease_guides"] = guides
            content_json["section2"] = sec2
        except Exception:
            pass
        return content_json

    async def _handle_generation_error(self, user_id: str | None, e: Exception) -> dict:
        print(f"OpenAI Error: {e}")
        try:
            await self.llm_service.update_or_create(
                user_id=user_id,
                data={
                    "activity": False,
                    "user_current_status": "Error occurred during generation",
                    "generated_content": {
                        "section1": {
                            "title": "오류 안내",
                            "status": "데이터 확인 불가",
                            "content": f"오류: {str(e)}",
                        },
                    },
                },
            )
        except Exception:
            pass

        return {
            "user_current_status": "Error occurred",
            "generated_content": {
                "section1": {
                    "title": "오류 안내",
                    "status": "데이터 확인 불가",
                    "content": "네트워크 연결 불안정 또는 API 오류",
                },
            },
            "activity": False,
            "created_at": datetime.now(),
        }

    async def get_saved_guide(self, user: User | None = None) -> dict:
        """
        저장된 생활가이드를 조회합니다.
        - 저장된 가이드가 있으면 그대로 반환
        - 없으면 새로 생성해서 저장 후 반환
        """
        if not user or not user.id:
            return {
                "user_current_status": "Guest User",
                "generated_content": {
                    "section1": {
                        "title": "안내",
                        "status": "로그인 필요",
                        "content": "로그인하시면 맞춤형 건강 가이드를 받아보실 수 있습니다.",
                    }
                },
                "activity": False,
                "created_at": datetime.now(),
            }

        saved = await self.llm_service.get_by_user_id(str(user.id))
        if saved:
            return {
                "user_current_status": saved.user_current_status,
                "generated_content": saved.generated_content,
                "activity": saved.activity,
                "created_at": saved.created_at,
            }

        return await self.generate_guide(str(user.id))
