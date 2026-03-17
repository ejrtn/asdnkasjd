from datetime import datetime
from zoneinfo import ZoneInfo

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

    @staticmethod
    def _to_kst_str(dt: datetime | None) -> str:
        if not dt:
            return ""
        raw = dt.replace(tzinfo=None)  # utc 로 간주하여 tzinfo 제거
        utc = raw.replace(tzinfo=ZoneInfo("UTC"))  # 명시적으로 UTC로 설정
        return utc.astimezone(ZoneInfo("Asia/Seoul")).isoformat()  # KST로 변환하여 ISO 포맷으로 반환

    # ==========================================
    # 필수 1: LLM 기반 안내 가이드 생성
    # ==========================================
    async def generate_guide(self, user_id: str | None, background_tasks=None) -> dict:
        """
        [GUIDE] 맞춤 가이드 생성 트리거.
        즉시 '생성 중' 상태를 반환하고, 실제 RAG 및 LLM 작업은 백그라운드에서 수행합니다.
        """
        # API 키가 없으면 더미 데이터 반환
        if not self.llm_service.client:
            return self._get_dummy_guide()

        # 1. 즉시 로딩 상태 저장 및 현재 데이터 반환 (프론트엔드 피드백용)
        # 이미 생성 중인 경우 중복 생성을 방지하거나 현재 상태를 그대로 반환
        saved = await self.llm_service.get_by_user_id(user_id)
        if saved and saved.activity is True:
            return {
                "user_current_status": saved.user_current_status,
                "generated_content": saved.generated_content,
                "activity": True,
                "created_at": saved.created_at,
            }

        # 상태 업데이트: 생성 중(activity=True)
        await self.update_loading_state(user_id)

        # 최신 상태 다시 로드
        current = await self.llm_service.get_by_user_id(user_id)

        # 2. 백그라운드에서 무거운 작업(RAG + LLM) 수행
        if background_tasks:
            background_tasks.add_task(self._run_guide_generation_task, user_id)
        else:
            # 백그라운드 태스크가 없는 경우 동기적으로 실행 (테스트 등)
            await self._run_guide_generation_task(user_id)

        return {
            "user_current_status": current.user_current_status if current else "가이드 생성 시작...",
            "generated_content": current.generated_content if current else {},
            "activity": True,
            "created_at": current.created_at if current else self._to_kst_str(datetime.now(ZoneInfo("UTC"))),
        }

    async def _run_guide_generation_task(self, user_id: str | None) -> None:
        """
        백그라운드에서 실행될 실제 가인드 생성 로직 (RAG + LLM)
        """
        try:
            # 1. 실제 사용자 데이터 조회
            health_data = await self._fetch_user_health_data(user_id)
            lifestyle = self._extract_lifestyle(health_data["profile"])

            # 2. RAG context 생성 (느림)
            rag_context = await self._generate_rag_context_str(health_data["disease_list"], lifestyle)

            # 3. Prompt 구성 및 LLM 생성 (느림)
            prompt = self._build_guide_prompt(health_data, lifestyle, rag_context)

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

            # 4. 질환 및 건강수칙 누락 보정 및 저장
            fixed_content = await self._fix_missing_diseases(content_json, health_data["disease_list"])
            fixed_content = self._fix_missing_health_guides(fixed_content)

            data = {
                "user_current_status": prompt,
                "generated_content": fixed_content,
                "activity": False,
                "created_at": datetime.now(tz=ZoneInfo("UTC")).replace(tzinfo=None),
            }
            await self.llm_service.update_or_create(user_id=user_id, data=data)

        except Exception as e:
            await self._handle_generation_error(user_id, e)

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
                "section3": {
                    "title": "오늘의 건강 관리 수칙",
                    "health_guides": [
                        {
                            "name": "운동",
                            "tips": ["주 3회, 30분 이상 가벼운 걷기 등 자신에게 맞는 운동을 꾸준히 실천해 보세요."],
                        },
                        {
                            "name": "식단",
                            "tips": ["규칙적인 식사와 균형 잡힌 영양 섭취가 면역력 유지에 도움이 됩니다."],
                        },
                        {"name": "수면", "tips": ["하루 7~8시간의 충분한 수면으로 몸의 피로를 풀어주세요."]},
                        {"name": "흡연/음주", "tips": ["금연과 절주는 모든 대사 질환 예방의 첫걸음입니다."]},
                    ],
                },
            },
            "activity": False,
            "created_at": self._to_kst_str(datetime.now(ZoneInfo("UTC"))),
        }

    async def update_loading_state(self, user_id: str | None) -> None:
        try:
            saved = await self.llm_service.get_by_user_id(user_id)
            await self.llm_service.update_or_create(
                user_id=user_id,
                data={
                    "activity": True,
                    "user_current_status": "AI가 맞춤 가이드를 생성 중입니다...",
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

    async def _fix_missing_diseases(self, content_json: dict, disease_list: list[str]) -> dict:
        try:
            sec2 = content_json.get("section2") or {}
            guides = sec2.get("disease_guides") or []

            guide_names = {
                self._normalize_disease_name(str(g.get("name")))
                for g in guides
                if isinstance(g, dict) and g.get("name")
            }

            for dname in disease_list:
                normalized_name = self._normalize_disease_name(dname)

                if normalized_name not in guide_names:
                    fallback_tips = await self._generate_llm_fallback_tips(normalized_name)

                    guides.append(
                        {
                            "name": dname,
                            "tips": fallback_tips,
                        }
                    )

            sec2["disease_guides"] = guides
            content_json["section2"] = sec2

        except Exception as e:
            print(f"[FIX MISSING DISEASES ERROR] {e}")

        return content_json

    def _fix_missing_health_guides(self, content_json: dict) -> dict:
        try:
            sec3 = content_json.get("section3") or {}
            guides = sec3.get("health_guides") or []

            # 현재 있는 카테고리 이름들 수집
            guide_names = {g.get("name") for g in guides if isinstance(g, dict)}

            required_categories = {
                "운동": "주 3회, 30분 이상 가벼운 걷기 등 자신에게 맞는 운동을 꾸준히 실천해 보세요.",
                "식단": "규칙적인 식사와 균형 잡힌 영양 섭취가 면역력 유지에 도움이 됩니다.",
                "수면": "하루 7~8시간의 충분한 수면으로 몸의 피로를 풀어주세요.",
                "흡연/음주": "금연과 절주는 모든 대사 질환 예방의 첫걸음입니다.",
            }

            # 누락된 필수 카테고리 강제 추가
            for req_name, default_tip in required_categories.items():
                # '흡연/음주' 처럼 복합어나 비슷한 이름이 처리안되는 경우를 위해 정확히 매칭
                if req_name not in guide_names:
                    guides.append({"name": req_name, "tips": [default_tip]})

            # (선택) UI의 정돈된 표시를 위해 고정된 순서로 정렬할 수 있으나, 일단 추가만으로 충분함
            sec3["health_guides"] = guides
            content_json["section3"] = sec3
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
            "created_at": self._to_kst_str(datetime.now(ZoneInfo("UTC"))),
        }

    def _normalize_disease_name(self, name: str) -> str:
        alias_map = {
            "목감기": "감기",
            "코감기": "감기",
            "몸살감기": "감기",
            "당뇨": "당뇨병",
            "고지혈증": "이상지질혈증",
        }
        return alias_map.get((name or "").strip(), (name or "").strip())

    async def _generate_llm_fallback_tips(self, disease_name: str) -> list[str]:
        try:
            prompt = f"""
    사용자의 질환명은 '{disease_name}' 입니다.

    이 질환에 대해 의료 진단이나 처방이 아닌,
    일반적인 생활관리 가이드를 2개 작성하세요.

    조건:
    - 쉬운 한국어
    - 과도한 단정 금지
    - 휴식, 수분 섭취, 식사, 운동, 증상 악화 시 병원 권고 중심
    - 반드시 JSON 형식으로만 답변

    형식:
    {{
    "tips": ["가이드1", "가이드2"]
    }}
    """.strip()

            result = await self.llm_service.generate_json(
                messages=[
                    {
                        "role": "system",
                        "content": "너는 안전한 건강생활 안내 도우미다. 반드시 JSON으로만 답변한다.",
                    },
                    {"role": "user", "content": prompt},
                ],
                model="gpt-4o-mini",
                temperature=0.3,
            )

            # 정상 JSON 처리
            if isinstance(result, dict):
                tips = result.get("tips", [])
                if isinstance(tips, list):
                    cleaned = [str(t).strip() for t in tips if str(t).strip()]
                    if cleaned:
                        return cleaned[:2]

            # 혹시 리스트로 오는 경우
            if isinstance(result, list):
                cleaned = [str(t).strip() for t in result if str(t).strip()]
                if cleaned:
                    return cleaned[:2]

        except Exception as e:
            print(f"[LLM FALLBACK ERROR] {e}")

        return [
            "해당 질환에 대한 일반 건강관리 가이드를 제공합니다.",
            "증상이 지속되거나 악화되면 의료진과 상담하세요.",
        ]

    async def get_saved_guide(self, user: User | None = None, background_tasks=None) -> dict:
        """
        저장된 생활가이드를 조회합니다.
        - 저장된 가이드가 있으면 그대로 반환
        - 없으면 백그라운드 생성 트리거 후 '생성 중' 상태 반환
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
                "created_at": self._to_kst_str(datetime.now(ZoneInfo("UTC"))),
            }

        saved = await self.llm_service.get_by_user_id(str(user.id))

        # 1. 저장된 가이드가 있고 '완료' 상태인 경우 즉시 반환
        if saved and saved.activity is False:
            fixed_content = self._fix_missing_health_guides(saved.generated_content or {})
            return {
                "user_current_status": saved.user_current_status,
                "generated_content": fixed_content,
                "activity": False,
                "created_at": saved.created_at,
            }

        # 2. 저장된 가이드가 없거나 '생성 중'인 경우
        return await self.generate_guide(str(user.id), background_tasks)
