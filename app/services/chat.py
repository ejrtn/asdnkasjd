import asyncio
from typing import Any

from app.dtos.chat import ChatRequest, ChatResponse
from app.models.user import User
from app.rag.context_builder import build_context_from_search_results
from app.rag.vector_store import search_similar_documents
from app.repositories.alarm import AlarmHistoryRepository, AlarmRepository
from app.repositories.blood_pressure_record import BloodPressureRecordRepository
from app.repositories.blood_sugar_record import BloodSugarRecordRepository
from app.repositories.chat_memory_repository import ChatMemoryRepository
from app.repositories.current_med import CurrentMedRepository
from app.repositories.health_profile import HealthProfileRepository
from app.repositories.llm_life_guide import LLMLifeGuideRepository
from app.services.llm_service import LLMService


class ChatService:
    def __init__(self):
        self.memory_repo = ChatMemoryRepository()
        self.llm_service = LLMService()

        self.llm_life_guide_repo = LLMLifeGuideRepository()
        self.bp_repo = BloodPressureRecordRepository()
        self.bs_repo = BloodSugarRecordRepository()
        self.alarm_repo = AlarmRepository()
        self.alarm_history_repo = AlarmHistoryRepository()
        self.current_med_repo = CurrentMedRepository()
        self.health_profile_repo = HealthProfileRepository()

    def detect_emergency(self, text: str) -> bool:
        """응급 상황 감지"""
        emergency_keywords = ["숨", "가슴", "호흡곤란", "흉통", "의식", "어지러움", "경련", "실신"]
        return any(keyword in text for keyword in emergency_keywords)

    def classify_question(self, text: str) -> str:
        """질문 분류"""
        if any(word in text for word in ["약", "복용", "복약", "처방"]):
            return "복약"
        elif any(word in text for word in ["알람", "알림", "리마인더", "설정된"]):
            return "알람"
        elif any(word in text for word in ["증상", "아프", "통증", "아픔"]):
            return "증상"
        else:
            return "일반"

    @staticmethod
    def _format_guide_section(section: dict | None, fallback: str) -> str:
        """JSON 가이드 섹션을 읽기 좋은 문자열로 변환"""
        if not section:
            return fallback
        import json

        if isinstance(section, dict):
            return json.dumps(section, ensure_ascii=False, indent=2)
        return str(section)

    @staticmethod
    def _format_alarm_time(alarm_time: object) -> str:
        """alarm_time이 time 또는 timedelta(MySQL TIME)일 수 있으므로 안전하게 HH:MM 문자열로 변환"""
        import datetime as dt

        if alarm_time is None:
            return "-"
        if isinstance(alarm_time, dt.time):
            return alarm_time.strftime("%H:%M")
        if isinstance(alarm_time, dt.timedelta):
            total_seconds = int(alarm_time.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes = remainder // 60
            return f"{hours:02d}:{minutes:02d}"
        return str(alarm_time)

    async def _build_user_health_context(self, user_id: str) -> str | None:
        """
        저장된 생활안내가이드 + 최근 혈압 + 최근 혈당 + 알람 + 오늘 알람 히스토리를 합쳐
        챗봇용 사용자 맞춤 건강 정보 문자열 생성
        """
        try:
            user = await User.get_or_none(id=user_id)
            if not user:
                return None

            # 병렬 데이터 조회 실행
            life_guide, bp_records, bs_records, current_meds, health_profile = await asyncio.gather(
                self.llm_life_guide_repo.get_by_user_id(user_id),
                self.bp_repo.get_by_user_id(user_id),
                self.bs_repo.get_by_user_id(user_id),
                self.current_med_repo.get_by_user_id(user_id),
                self.health_profile_repo.get_by_user_id(user_id),
            )

            recent_bp = bp_records[:5]
            recent_bs = bs_records[:5]

            bp_lines = [
                f"- {record.systolic}/{record.diastolic} mmHg ({record.measure_type}, {record.created_at.strftime('%Y-%m-%d %H:%M')})"
                for record in recent_bp
            ] or ["- 최근 혈압 기록 없음"]

            bs_lines = [
                f"- {record.glucose_mg_dl} mg/dL ({record.measure_type}, {record.created_at.strftime('%Y-%m-%d %H:%M')})"
                for record in recent_bs
            ] or ["- 최근 혈당 기록 없음"]

            med_lines = []
            for med in current_meds:
                parts = [f"- {med.medication_name}"]
                if med.one_dose_amount:
                    parts.append(f"{med.one_dose_amount}")
                if med.instructions:
                    parts.append(f"({med.instructions})")
                med_lines.append(" ".join(parts))
            med_lines = med_lines or ["- 등록된 복용 약물 없음"]

            # 건강 프로필 정보
            if health_profile:
                profile_lines = [
                    f"- 키: {health_profile.height_cm}cm / 몸무게: {health_profile.weight_kg}kg",
                    f"- 최근 체중 변화: {health_profile.weight_change}",
                    f"- 수면: {health_profile.sleep_hours}시간 / 변화: {health_profile.sleep_change}"
                    if health_profile.sleep_hours
                    else f"- 수면 변화: {health_profile.sleep_change}",
                    f"- 흡연: {health_profile.smoking_status}",
                    f"- 음주: {health_profile.drinking_status}",
                    f"- 운동: {health_profile.exercise_frequency}",
                    f"- 식습관: {health_profile.diet_type}",
                    f"- 가족력: {health_profile.family_history}",
                ]
            else:
                profile_lines = ["- 등록된 건강 프로필 없음"]

            # 생활안내 가이드 섹션별 파싱
            guide_status = life_guide.user_current_status if life_guide else "저장된 상태 정보 없음"
            medication_guide = self._format_guide_section(
                life_guide.medication_guide if life_guide else None, "복약/알레르기 가이드 없음"
            )
            disease_guide = self._format_guide_section(
                life_guide.disease_guide if life_guide else None, "기저질환 가이드 없음"
            )
            profile_guide = self._format_guide_section(
                life_guide.profile_guide if life_guide else None, "생활습관 가이드 없음"
            )

            # 알람 정보 및 히스토리 조회 병렬 실행
            alarm_lines_task = self._build_alarm_lines(user_id)
            history_lines_task = self._build_alarm_history_lines(user_id)
            alarm_lines, history_lines = await asyncio.gather(alarm_lines_task, history_lines_task)

            return f"""[사용자 맞춤 건강 정보 — 이 데이터는 실제 DB에서 조회한 사용자의 정보입니다. 사용자가 관련 질문을 하면 반드시 이 데이터를 기반으로 답변하세요.]

사용자 상태 요약 (기저질환+알러지+현재약물):
{guide_status}

AI 생활안내 가이드 - 복약 및 알레르기:
{medication_guide}

AI 생활안내 가이드 - 기저질환 지침:
{disease_guide}

AI 생활안내 가이드 - 생활습관 (혈압/혈당 포함):
{profile_guide}

사용자 건강 프로필 (키/몸무게/생활습관):
{chr(10).join(profile_lines)}

현재 복용 중인 약물:
{chr(10).join(med_lines)}

최근 혈압 기록:
{chr(10).join(bp_lines)}

최근 혈당 기록:
{chr(10).join(bs_lines)}

현재 활성 알람:
{chr(10).join(alarm_lines)}

오늘 알람 발송 내역:
{chr(10).join(history_lines)}
""".strip()

        except Exception as e:
            print(f"[ChatService] user health context build failed: {e}")
            return None

    async def _build_alarm_lines(self, user_id: str) -> list[str]:
        """활성 알람 목록을 문자열 리스트로 변환"""
        active_alarms = await self.alarm_repo.get_active_alarms_by_user_id(user_id)
        lines = []
        for alarm in active_alarms:
            med_name = "-"
            try:
                if alarm.current_med_id and alarm.current_med:
                    med_name = alarm.current_med.medication_name
            except Exception:
                pass
            time_str = self._format_alarm_time(alarm.alarm_time)
            lines.append(f"- [{alarm.alarm_type}] {time_str} / 약: {med_name}")
        return lines or ["- 설정된 알람 없음"]

    async def _build_alarm_history_lines(self, user_id: str) -> list[str]:
        """오늘 알람 히스토리를 문자열 리스트로 변환"""
        from datetime import datetime

        from app.core.config import config

        now_kst = datetime.now(config.TIMEZONE)
        today_histories = await self.alarm_history_repo.get_today_histories_by_user_id(user_id, now_kst)
        lines = []
        for h in today_histories:
            a_type = h.alarm.alarm_type if h.alarm else "-"
            med_name = "-"
            try:
                if h.alarm and h.alarm.current_med_id and h.alarm.current_med:
                    med_name = h.alarm.current_med.medication_name
            except Exception:
                pass
            sent = h.sent_at_kst.strftime("%H:%M") if h.sent_at_kst else "-"
            confirmed = "✅ 확인" if h.is_confirmed else "❌ 미확인"
            lines.append(f"- [{a_type}] {sent} / 약: {med_name} / {confirmed}")
        return lines or ["- 오늘 발송된 알람 없음"]

    async def process_chat(self, request: ChatRequest) -> ChatResponse:
        """
        MongoDB 저장 + RAG 기반 챗봇 응답 생성
        """
        # 1. 세션 ID 생성/유지
        session_id = request.session_id or self.memory_repo.create_session_id()

        # 2. 최근 메시지 추출
        recent_msg = request.messages[-1].content if request.messages else ""

        # 3. 응급 상황 감지
        is_emergency = self.detect_emergency(recent_msg)
        q_type = self.classify_question(recent_msg)
        r_level = "Emergency" if is_emergency else "Normal"

        # 4. 사용자 메시지 저장
        await self.memory_repo.save_message(
            session_id=session_id,
            user_id=request.user_id,
            role="user",
            content=recent_msg,
            question_type=q_type,
            risk_level=r_level,
        )

        # 5. 응급 상황 처리
        if is_emergency:
            reply = "호흡곤란이나 흉통이 느껴지신다면 즉시 가까운 응급실을 방문하시거나 119에 연락하시기 바랍니다."
        else:
            # 6. 최근 대화 이력 조회
            recent_history = await self.memory_repo.get_recent_messages(session_id, request.user_id)

            # 6.5 사용자 맞춤 건강 정보 조회 (저장된 데이터 기반)
            user_health_context = await self._build_user_health_context(request.user_id)

            # 7. RAG 문서 검색 (ChromaDB 벡터 검색)
            search_results = search_similar_documents(
                query_text=recent_msg,
                n_results=5,
            )
            rag_context = build_context_from_search_results(
                results_list=[search_results],
                max_docs=5,
                include_metadata=True,
            )

            # 8. 메시지 구성 (개선된 방식)
            system_prompt = """당신은 Cloud9 Care의 건강 상담 AI 비서입니다.
사용자의 복약 관리, 건강 상담, 증상 문의에 친절하고 정확하게 답변해주세요.
의학적 진단은 하지 말고, 필요시 전문의와 상담을 권유하세요.
답변은 간결하고 친근하게 작성해주세요.

중요 규칙:
- 아래에 [사용자 맞춤 건강 정보]가 제공됩니다. 이것은 실제 DB에서 조회한 이 사용자의 데이터입니다.
- 사용자가 약, 복용 약물, 먹는 약을 물어보면 → '현재 복용 중인 약물' 데이터와 'AI 생활안내 가이드 - 복약 및 알레르기' 데이터를 기반으로 답변하세요.
- 사용자가 혈압을 물어보면 → '최근 혈압 기록'과 'AI 생활안내 가이드 - 생활습관' 데이터를 기반으로 답변하세요.
- 사용자가 혈당을 물어보면 → '최근 혈당 기록'과 'AI 생활안내 가이드 - 생활습관' 데이터를 기반으로 답변하세요.
- 사용자가 질환, 기저질환을 물어보면 → '사용자 상태 요약'과 'AI 생활안내 가이드 - 기저질환 지침' 데이터를 기반으로 답변하세요.
- 사용자가 건강 상태, 생활습관을 물어보면 → 모든 AI 생활안내 가이드 섹션을 종합적으로 활용하세요.
- 사용자가 키, 몸무게, BMI, 체중, 수면, 흡연, 음주, 운동, 식습관을 물어보면 → '사용자 건강 프로필' 데이터를 기반으로 답변하세요.
- 사용자가 알람, 알림을 물어보면 → '현재 활성 알람'과 '오늘 알람 발송 내역' 데이터를 기반으로 답변하세요.
- 절대로 "정보를 가지고 있지 않다", "접근할 수 없다"고 답변하지 마세요. 데이터가 제공되어 있습니다.
- 사용자가 묻지 않은 건강 상태를 먼저 길게 나열하지 마세요.
- 응급이 의심되는 표현이 있으면 즉시 119 또는 응급실 방문을 우선 권고하세요.
- 건강 정보 답변 시 [참고 의료 정보]로 제공된 질병관리청/국가건강정보포털 기반 자료를 우선적으로 활용하고, 답변 마지막에 출처를 간략히 안내하세요 (예: "질병관리청 건강정보 기준").
- 참고 자료에 없는 내용은 임의로 지어내지 말고, "정확한 정보는 담당 의료진과 상담해주세요"라고 안내하세요."""

            messages = [{"role": "system", "content": system_prompt}]

            # 사용자 맞춤 건강 정보 추가
            if user_health_context:
                messages.append({"role": "system", "content": user_health_context})

            # 이전 대화 이력 추가 (현재 메시지 제외)
            for msg in recent_history[:-1]:  # 현재 메시지 제외
                role = msg["role"]
                # OpenAI API에서 허용하는 role로 정규화
                if role not in {"system", "user", "assistant"}:
                    role = "assistant"
                messages.append({"role": role, "content": msg["content"]})

            # 참고 문서 추가
            if rag_context:
                messages.append({"role": "system", "content": rag_context})

            # 현재 사용자 질문
            messages.append({"role": "user", "content": recent_msg})

            # 9. OpenAI 호출
            try:
                reply = await self.llm_service.generate_text(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500,
                )
                if not reply:
                    reply = "응답을 생성할 수 없습니다."
            except Exception as e:
                print(f"[ChatService] llm generate failed: {e}")
                reply = "죄송합니다. 일시적인 오류가 발생했습니다. 다시 시도해주세요."

        # 10. AI 응답 저장
        await self.memory_repo.save_message(
            session_id=session_id,
            user_id=request.user_id,
            role="assistant",
            content=reply,
            question_type=q_type,
            risk_level=r_level,
        )

        return ChatResponse(
            session_id=session_id,
            question_type=q_type,
            risk_level=r_level,
            reply=reply,
            multimodal_assets=[],
        )

    async def end_chat_session(self, session_id: str, user_id: str | None = None) -> bool:
        """채팅 세션 종료 (소유자 검증 포함)"""
        # 소유자 검증
        if user_id and not await self.memory_repo.verify_session_owner(session_id, user_id):
            return False
        return bool(await self.memory_repo.end_session(session_id, user_id))

    async def get_chat_history(self, session_id: str, user_id: str) -> list[dict[str, Any]]:
        """채팅 대화 내역 조회 (소유자 검증 포함)"""
        # 소유자 검증
        if not await self.memory_repo.verify_session_owner(session_id, user_id):
            return []

        messages = await self.memory_repo.get_recent_messages_for_history(session_id, user_id)

        return [
            {
                "role": msg["role"],
                "content": msg["content"],
                "created_at": msg["created_at"].isoformat() if msg.get("created_at") else None,
                "risk_level": msg.get("risk_level", "Normal"),
            }
            for msg in messages
        ]

    async def stream_chat(self, request: ChatRequest):
        """
        챗봇의 응답을 토큰 단위로 실시간 스트리밍(SSE)하여 제공합니다.

        Args:
            request (ChatRequest): 메시지 내역 및 세션 정보

        Yields:
            str: SSE 형식의 JSON 데이터 문자열
        """
        import asyncio
        import json

        full_text = "이것은 실시간 스트리밍 응답 샘플입니다. 토큰 단위로 데이터가 전송됩니다."
        for word in full_text.split():
            yield f"data: {json.dumps({'text': word + ' '})}\n\n"
            await asyncio.sleep(0.1)
        yield "data: [DONE]\n\n"
