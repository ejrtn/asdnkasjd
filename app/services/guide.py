import asyncio
import hashlib
import json
import logging
from datetime import datetime
from typing import Any, cast
from zoneinfo import ZoneInfo

from app.models.allergy import Allergy
from app.models.blood_pressure_record import BloodPressureRecord
from app.models.blood_sugar_record import BloodSugarRecord
from app.models.chronic_disease import ChronicDisease
from app.models.current_med import CurrentMed
from app.models.health_profile import HealthProfile
from app.models.llm_life_guide import LLMLifeGuide
from app.models.user import User
from app.rag.rag_pipeline import generate_rag_context
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


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
    # 모듈형 가이드 생성 (MEDICATION / DISEASE / PROFILE)
    # ==========================================
    async def generate_modular_guide(self, user_id: str, section_type: str, background_tasks=None) -> None:
        """
        특정 섹션에 대해 모듈화된 가이드 생성을 트리거합니다.
        """
        if not self.llm_service.client:
            return

        # 해당 섹션의 생성 상태를 True로 변경
        await self.update_loading_state(user_id, section_type, True)

        if background_tasks:
            background_tasks.add_task(self._run_modular_generation_task, user_id, section_type)
        else:
            await self._run_modular_generation_task(user_id, section_type)

    async def _run_modular_generation_task(self, user_id: str, section_type: str) -> None:
        """
        백그라운드에서 섹션별 태스크 실행
        """
        try:
            if section_type == "MEDICATION":
                await self._run_medication_guide_task(user_id)
            elif section_type == "DISEASE":
                await self._run_disease_guide_task(user_id)
            elif section_type == "PROFILE":
                await self._run_profile_guide_task(user_id)

            # 해당 작업 완료 시 상태 변경 False 처리
            await self.update_loading_state(user_id, section_type, False)
        except Exception as e:
            await self._handle_generation_error(user_id, section_type, e)

    async def _get_guide_record(self, user_id: str) -> LLMLifeGuide:
        """최신 가이드 레코드를 가져오거나 생성합니다."""
        guide = await LLMLifeGuide.filter(user_id=user_id).order_by("-created_at").first()
        if not guide:
            guide = cast(LLMLifeGuide, await LLMLifeGuide.create(user_id=user_id, user_current_status="가이드 생성 중"))
        return guide

    async def _run_medication_guide_task(self, user_id: str) -> None:
        """복약 가이드(section1) 생성 - 알약만 별개"""
        health_data = await self._fetch_user_health_data(user_id)
        current_data = {"med_list": health_data["med_list"]}
        fingerprint = self._calculate_fingerprint(current_data)

        guide_record = await self._get_guide_record(user_id)
        if guide_record.medication_guide and guide_record.medication_guide.get("_fingerprint") == fingerprint:
            return  # 변동 없음

        prompt = self._build_medication_prompt(health_data)
        try:
            content = await self.llm_service.generate_json(
                messages=[
                    {"role": "system", "content": "복약 지도 전문 의사로서 조언한다. JSON으로만 답변한다."},
                    {"role": "user", "content": prompt},
                ],
                model="gpt-4o-mini",
                temperature=0.3,
            )
            content["_fingerprint"] = fingerprint
            await self._save_modular_result(guide_record, "medication_guide", content)
        except Exception as e:
            print(f"[Medication Task Error] {e}")

    def _build_medication_prompt(self, health_data: dict) -> str:
        return f"""
        당신은 환자의 복약 안전을 관리하는 의사입니다. 아래 약물 목록을 바탕으로 복약 지침을 작성하세요.

        [복용 중인 약물]
        {", ".join(health_data["med_list"]) if health_data["med_list"] else "없음"}

        [작성 지침]
        1. 현재 복용 중인 약물들 간의 상호작용 또는 주의사항을 체크하세요.
        2. 'status': '상호작용 없음', '주의 필요', '위험 가능성' 중 하나를 선택하세요.
        3. 'content': 환자가 이해하기 쉬운 상세 설명을 작성하세요.
        4. 'general_cautions': 일반적인 복약 주의사항을 리스트로 작성하세요.

        [응답 형식]
        {{
            "title": "복약 안전성 및 주의사항",
            "status": "...",
            "content": "...",
            "general_cautions": ["...", "..."]
        }}
        """.strip()

    async def _save_modular_result(self, guide: LLMLifeGuide, field_name: str, content: dict) -> None:
        """모듈화된 결과를 특정 컬럼에 저장합니다."""
        setattr(guide, field_name, content)
        # 모든 섹션이 채워졌는지 확인하여 activity 상태를 조정할 수도 있지만,
        # 여기서는 단순히 섹션만 업데이트합니다.
        await guide.save(update_fields=[field_name])

    async def _run_disease_guide_task(self, user_id: str) -> None:
        """질환 및 알레르기 가이드(section2) 생성"""
        health_data = await self._fetch_user_health_data(user_id)
        current_data = {"disease_list": health_data["disease_list"], "allergy_list": health_data["allergy_list"]}
        fingerprint = self._calculate_fingerprint(current_data)

        guide_record = await self._get_guide_record(user_id)
        if guide_record.disease_guide and guide_record.disease_guide.get("_fingerprint") == fingerprint:
            return

        prompt = self._build_disease_prompt(health_data)
        try:
            content = await self.llm_service.generate_json(
                messages=[
                    {"role": "system", "content": "질환 및 알레르기 관리 전문의로서 조언한다. JSON으로만 답변한다."},
                    {"role": "user", "content": prompt},
                ],
                model="gpt-4o-mini",
                temperature=0.3,
            )
            content["_fingerprint"] = fingerprint
            await self._save_modular_result(guide_record, "disease_guide", content)
        except Exception as e:
            print(f"[Disease Task Error] {e}")

    def _build_disease_prompt(self, health_data: dict) -> str:
        return f"""
        당신은 만성 질환 및 알레르기 관리 전문의입니다. 아래 정보를 바탕으로 환자 맞춤형 생활 지침을 작성하세요.

        [환자 질환]
        {", ".join(health_data["disease_list"]) if health_data["disease_list"] else "없음"}

        [알레르기 정보]
        {", ".join(health_data["allergy_list"]) if health_data["allergy_list"] else "없음"}

        [작성 지침]
        1. 질환과 알레르기 정보를 결합하여 환자가 일상에서 주의해야 할 핵심 관리 수칙을 'disease_guides'에 담으세요.
        2. 만약 질환이나 알레르기가 없다면, 해당 카테고리에 맞는 일반적인 예방 수칙을 제공해 주세요.
        3. 'integrated_point': 질환과 알레르기를 통합하여 관리해야 할 핵심 포인트를 작성하세요.

        [응답 형식]
        {{
            "title": "질환 및 알레르기 관리 가이드",
            "disease_guides": [
                {{ "name": "항목명(질환 또는 알레르기)", "tips": ["지침1", "지침2"] }}
            ],
            "integrated_point": "..."
        }}
        """.strip()

    async def _run_profile_guide_task(self, user_id: str) -> None:
        """생활 습관 가이드(section3) 생성"""
        health_data = await self._fetch_user_health_data(user_id)
        lifestyle = self._extract_lifestyle(health_data["profile"])

        # 핑거프린트: 프로필 + 최신 BP/BS
        current_data = {"lifestyle": lifestyle, "bp": health_data["bp_list"], "bs": health_data["bs_list"]}
        fingerprint = self._calculate_fingerprint(current_data)

        guide_record = await self._get_guide_record(user_id)
        if guide_record.profile_guide and guide_record.profile_guide.get("_fingerprint") == fingerprint:
            return

        # RAG Context (질환별 생활수칙 참고용)
        rag_context = await self._generate_rag_context_str(health_data["disease_list"], lifestyle)
        prompt = self._build_profile_prompt(health_data, lifestyle, rag_context)

        try:
            content = await self.llm_service.generate_json(
                messages=[
                    {"role": "system", "content": "건강 코치로서 조언한다. JSON으로만 답변한다."},
                    {"role": "user", "content": prompt},
                ],
                model="gpt-4o-mini",
                temperature=0.4,
            )
            content["_fingerprint"] = fingerprint
            # 누락된 4대 카테고리 보정
            content = self._fix_missing_health_guides({"section3": content})["section3"]
            await self._save_modular_result(guide_record, "profile_guide", content)
        except Exception as e:
            print(f"[Profile Task Error] {e}")

    def _build_profile_prompt(self, health_data: dict, lifestyle: dict, rag_context: str) -> str:
        s_hours = lifestyle.get("sleep_hours")
        s_hours_text = f"{s_hours}시간" if s_hours is not None else "정보 없음"

        return f"""
        당신은 건강 관리 코치입니다. 환자의 생활 습관과 최신 활력 징후를 바탕으로 '오늘의 건강 관리 수칙'을 작성하세요.

        [환자 정보]
        - 최근 혈압: {", ".join(health_data["bp_list"]) if health_data["bp_list"] else "없음"}
        - 최근 혈당: {", ".join(health_data["bs_list"]) if health_data["bs_list"] else "없음"}
        - 흡연: {lifestyle.get("smoking_status") or "정보 없음"}
        - 음주: {lifestyle.get("drinking_status") or "정보 없음"}
        - 운동: {lifestyle.get("exercise_frequency") or "정보 없음"}
        - 식습관: {lifestyle.get("diet_type") or "정보 없음"}
        - 수면: {s_hours_text} ({lifestyle.get("sleep_change") or "변화 없음"})

        [참고 지침 (RAG)]
        {rag_context}

        [작성 지침]
        1. 'health_guides': '운동', '식단', '수면', '흡연/음주' 4가지 카테고리를 반드시 포함하여 각각 1~2개의 팁을 작성하세요.
        2. 카드 형태의 UI에 표시될 것이므로 간결하고 실천 가능한 조언을 제공하세요.

        [응답 형식]
        {{
            "title": "오늘의 건강 관리 수칙",
            "health_guides": [
                {{ "name": "운동", "tips": ["걷기 30분 추천"] }},
                {{ "name": "식단", "tips": ["저염식 실천"] }},
                {{ "name": "수면", "tips": ["규칙적인 수면"] }},
                {{ "name": "흡연/음주", "tips": ["금연 권장"] }}
            ]
        }}
        """.strip()

    def _calculate_fingerprint(self, data: Any) -> str:
        """데이터의 MD5 핑거프린트를 계산합니다."""
        dumped = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(dumped.encode("utf-8")).hexdigest()

    async def update_loading_state(self, user_id: str | None, section_type: str, is_active: bool) -> None:
        try:
            saved = await self.llm_service.get_by_user_id(user_id)
            data_to_update = {
                f"activity_{section_type.lower()}": is_active,
                "user_current_status": "AI가 맞춤 가이드를 생성 중입니다..."
                if getattr(saved, "activity", False) or is_active
                else "가이드 생성 완료",
            }
            await self.llm_service.update_or_create(
                user_id=user_id,
                data=data_to_update,
            )
        except Exception:
            pass

    async def _fetch_user_health_data(self, user_id: str | None) -> dict:
        try:
            # 병렬 실행 (asyncio.gather 사용)
            diseases_task = ChronicDisease.filter(user_id=user_id).all()
            allergies_task = Allergy.filter(user_id=user_id).all()
            meds_task = CurrentMed.filter(user_id=user_id).all()
            profile_task = HealthProfile.get_or_none(user_id=user_id)
            bp_records_task = BloodPressureRecord.filter(user_id=user_id).order_by("-created_at").limit(1)
            bs_records_task = BloodSugarRecord.filter(user_id=user_id).order_by("-created_at").limit(1)

            diseases, allergies, meds, profile, bp_records, bs_records = await asyncio.gather(
                diseases_task, allergies_task, meds_task, profile_task, bp_records_task, bs_records_task
            )

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

    async def _handle_generation_error(self, user_id: str | None, section_type: str, e: Exception) -> dict:
        print(f"OpenAI Error: {e}")
        try:
            await self.llm_service.update_or_create(
                user_id=user_id,
                data={
                    f"activity_{section_type.lower()}": False,
                    "user_current_status": "Error occurred during generation",
                },
            )
        except Exception:
            pass

        return {
            "user_current_status": "Error occurred",
            "generated_content": {
                "section1": {
                    "title": "안내",
                    "status": "데이터 확인 불가",
                    "content": "가이드 생성 중 오류가 발생했습니다. 잠시 후 상단의 새로고침 아이콘을 눌러보세요.",
                },
                "section2": {
                    "title": "질환 기반 생활습관 가이드",
                    "disease_guides": [],
                    "integrated_point": "",
                },
                "section3": {
                    "title": "오늘의 건강 관리 수칙",
                    "health_guides": [],
                },
            },
            "activity": False,
            "created_at": self._to_kst_str(datetime.now(ZoneInfo("UTC"))),
        }

    async def get_saved_guide(self, user: User | None = None, background_tasks=None) -> dict:
        """
        저장된 생활가이드를 조회합니다.
        - 저장된 가이드가 있으면 그대로 반환
        - 없으면 백그라운드 생성 트리거 후 '생성 중' 상태 반환
        """
        if not user:
            return {
                "user_current_status": "로그인이 필요합니다.",
                "generated_content": {},
                "activity": False,
                "created_at": self._to_kst_str(datetime.now(ZoneInfo("UTC"))),
            }

        saved = await LLMLifeGuide.filter(user_id=str(user.id)).order_by("-created_at").first()

        # 1. 저장된 가이드가 있는 경우, 모듈화된 컬럼들을 합쳐서 반환
        if saved:
            merged_content = {}
            if saved.medication_guide:
                merged_content["section1"] = saved.medication_guide
            if saved.disease_guide:
                merged_content["section2"] = saved.disease_guide
            if saved.profile_guide:
                merged_content["section3"] = saved.profile_guide

            # 꿀팁: 프론트에서 activity=True면 계속 로딩 아이콘을 띄우므로,
            # 모든 섹션이 채워져 있거나 생성 중이 아닐 때 적절히 False 반환
            fixed_content = self._fix_missing_health_guides(merged_content)
            return {
                "user_current_status": saved.user_current_status,
                "generated_content": fixed_content,
                "activity": bool(saved.activity_medication or saved.activity_disease or saved.activity_profile),
                "created_at": self._to_kst_str(saved.created_at),
            }

        # 2. 저장된 가이드가 전혀 없는 경우 최초 생성 트리거 (전체 섹션)
        async def _trigger_all():
            await asyncio.gather(
                self.generate_modular_guide(str(user.id), "MEDICATION"),
                self.generate_modular_guide(str(user.id), "DISEASE"),
                self.generate_modular_guide(str(user.id), "PROFILE"),
            )

        if background_tasks:
            background_tasks.add_task(_trigger_all)
        else:
            await _trigger_all()

        return {
            "user_current_status": "가이드 생성 시작...",
            "generated_content": {},
            "activity": True,
            "created_at": self._to_kst_str(datetime.now(ZoneInfo("UTC"))),
        }
