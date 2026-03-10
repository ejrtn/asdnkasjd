from datetime import datetime

from app.models.allergy import Allergy
from app.models.blood_pressure_record import BloodPressureRecord
from app.models.blood_sugar_record import BloodSugarRecord
from app.models.chronic_disease import ChronicDisease
from app.models.current_med import CurrentMed
from app.models.user import User
from app.services.llm_service import LLMService
from app.services.rag_service import RagService


class GuideService:
    def __init__(self):
        self.llm_service = LLMService()
        self.rag_service = RagService()

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
            # If API key is missing, return a dummy JSON directly to show the UI
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

        # 1. 즉시 로딩 상태 저장 (프론트엔드 피드백용)
        try:
            # 기존 데이터가 있으면 유지, 없으면 기본값으로 생성
            await self.llm_service.update_or_create(
                user_id=user_id,
                data={
                    "activity": True,
                    "user_current_status": "가이드 생성 중...",
                    "generated_content": (await self.llm_service.get_by_user_id(user_id)).generated_content
                    if await self.llm_service.get_by_user_id(user_id)
                    else {},
                },
            )
        except Exception:
            pass

        # 2. 실제 사용자 데이터 조회 (연결 실패 시 빈 데이터 처리)
        try:
            diseases = await ChronicDisease.filter(user_id=user_id).all()
            allergies = await Allergy.filter(user_id=user_id).all()
            meds = await CurrentMed.filter(user_id=user_id).all()

            # 최근 혈압, 혈당 데이터
            bp_records = await BloodPressureRecord.filter(user_id=user_id).order_by("-created_at").limit(1)
            bs_records = await BloodSugarRecord.filter(user_id=user_id).order_by("-created_at").limit(1)

            bp_list = [f"{r.systolic}/{r.diastolic} mmHg" for r in bp_records]
            bs_list = [f"{r.glucose_mg_dl} mg/dL ({r.measure_type})" for r in bs_records]

            disease_list = [d.disease_name for d in diseases]
            allergy_list = [a.allergy_name for a in allergies]
            med_list = [m.medication_name for m in meds]

        except Exception:
            # DB 오류 발생 시 빈 데이터로 처리
            disease_list, allergy_list, med_list = [], [], []
            bp_list = []
            bs_list = []

        keywords = self.rag_service.build_health_keywords(disease_list, med_list)

        selected_docs = self.rag_service.select_relevant_docs_by_keywords(
            keywords=keywords,
            max_docs=3,
        )
        rag_context = self.rag_service.build_rag_context(selected_docs)

        prompt = f"""
    신중하고 전문적인 의료 도우미로서, 아래 환자의 건강 상태를 바탕으로 '생활 안내 가이드'를 작성해줘.

    [환자 상태]
    - 만성 질환: {", ".join(disease_list) if disease_list else "없음"}
    - 알레르기: {", ".join(allergy_list) if allergy_list else "없음"}
    - 현재 복용 약: {", ".join(med_list) if med_list else "없음"}
    - 최근 혈압 기록: {", ".join(bp_list) if bp_list else "없음"}
    - 최근 혈당 기록: {", ".join(bs_list) if bs_list else "없음"}

    [참고 문서]
    {rag_context}

    [작성 가이드라인]
    1. 과한 확정 진단(예: ~병입니다)은 피하고, '권장합니다', '주의가 필요합니다' 등의 조언 톤을 유지할 것.
    2. 약물 상호작용 및 알레르기 성분을 최우선으로 체크할 것.
    3. 반드시 아래의 JSON 구조로 응답할 것.
    4. 만성 질환이 2개 이상이면 disease_guides를 질환 개수만큼 반드시 생성할 것(누락 금지).
    5. disease_guides의 name은 입력된 만성 질환명(disease_list)에 있는 문자열을 그대로 사용할 것.
    6. 참고 문서의 내용을 우선 반영하여 생활습관 및 복약 안내를 작성할 것.

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
        "title": "오늘의 실행 플랜",
        "checklist": ["체크리스트 1", "체크리스트 2", "체크리스트 3"]
    }},
    "section4": {{
        "title": "왜 이런 가이드가 생성되었나요?",
        "reason": "입력된 정보(질환, 약물 등)가 가이드에 어떻게 반영되었는지에 대한 설명"
    }},
    "disclaimer": "본 서비스는 의료 진단이나 처방을 제공하지 않으며, 참고용 안내입니다."
    }}
    """.strip()

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
            # ✅ 질환 누락 보정: disease_list에 있는 질환은 모두 disease_guides에 포함되도록 강제
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

            data = {"user_current_status": prompt, "generated_content": content_json, "activity": False}
            await self.llm_service.update_or_create(user_id=user_id, data=data)

            return {
                "user_current_status": prompt,
                "generated_content": content_json,
                "activity": False,
                "created_at": datetime.now(),
            }
        except Exception as e:
            print(f"OpenAI Error: {e}")
            # 에러 발생 시 activity를 False로 설정하여 무한 폴링 방지
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
