from typing import Any

from app.dtos.chat import ChatRequest, ChatResponse
from app.models.user import User
from app.repositories.chat_memory_repository import ChatMemoryRepository
from app.services.guide import GuideService
from app.services.llm_service import LLMService
from app.services.rag_service import RagService


class ChatService:
    def __init__(self):
        self.memory_repo = ChatMemoryRepository()
        self.llm_service = LLMService()
        self.guide_service = GuideService()
        self.rag_service = RagService()

    def detect_emergency(self, text: str) -> bool:
        """응급 상황 감지"""
        emergency_keywords = ["숨", "가슴", "호흡곤란", "흉통", "의식", "어지러움", "경련", "실신"]
        return any(keyword in text for keyword in emergency_keywords)

    def classify_question(self, text: str) -> str:
        """질문 분류"""
        if any(word in text for word in ["약", "복용", "복약", "처방"]):
            return "복약"
        elif any(word in text for word in ["증상", "아프", "통증", "아픔"]):
            return "증상"
        else:
            return "일반"

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

            # 6.5 사용자 맞춤 생활안내 가이드 생성
            guide_summary = None
            try:
                user = await User.get_or_none(id=request.user_id)
                if user:
                    # 현재 복용약 직접 조회
                    from app.models.current_med import CurrentMed

                    current_meds = await CurrentMed.filter(user=user).all()
                    med_names = [med.medication_name for med in current_meds]

                    # 가이드 생성
                    guide = await self.guide_service.generate_guide(user)
                    guide_data = guide.get("guide_data", {})

                    section1 = guide_data.get("section1", {})
                    section2 = guide_data.get("section2", {})
                    section3 = guide_data.get("section3", {})

                    guide_summary = f"""현재 복용약: {", ".join(med_names) if med_names else "등록된 약물 없음"}
복약 주의 상태: {section1.get("status", "정보 없음")}
복약 주의 요약: {section1.get("content", "정보 없음")}
질환 생활 가이드: {section2.get("integrated_point", "정보 없음")}
오늘 실행 플랜: {", ".join(section3.get("checklist", [])) if section3.get("checklist") else "정보 없음"}""".strip()
            except Exception:
                guide_summary = None

            # 7. RAG 문서 검색
            keywords = self.rag_service.extract_keywords_from_query(recent_msg)
            relevant_docs = self.rag_service.select_relevant_docs_by_keywords(keywords, max_docs=3)
            rag_context = self.rag_service.build_rag_context(relevant_docs)

            # 8. 메시지 구성 (개선된 방식)
            system_prompt = """당신은 Cloud9 Care의 건강 상담 AI 비서입니다.
사용자의 복약 관리, 건강 상담, 증상 문의에 친절하고 정확하게 답변해주세요.
의학적 진단은 하지 말고, 필요시 전문의와 상담을 권유하세요.
답변은 간결하고 친근하게 작성해주세요.
사용자 맞춤 건강 정보가 있더라도, 사용자가 묻지 않은 약 목록, 알람 일정, 건강 상태를 먼저 나열하지 마세요.
질문과 직접 관련된 경우에만 사용자 맞춤 정보를 활용해 답변하세요.
응급이 의심되는 표현이 있으면 즉시 119 또는 응급실 방문을 우선 권고하세요."""

            messages = [{"role": "system", "content": system_prompt}]

            # 사용자 맞춤 건강 정보 추가
            if guide_summary:
                messages.append({"role": "system", "content": f"[사용자 맞춤 건강 정보]\n{guide_summary}"})

            # 이전 대화 이력 추가 (현재 메시지 제외)
            for msg in recent_history[:-1]:  # 현재 메시지 제외
                role = msg["role"]
                # OpenAI API에서 허용하는 role로 정규화
                if role not in {"system", "user", "assistant"}:
                    role = "assistant"
                messages.append({"role": role, "content": msg["content"]})

            # 참고 문서 추가
            if relevant_docs:
                messages.append({"role": "system", "content": f"[참고 문서]\n{rag_context}"})

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
            except Exception:
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
        return bool(await self.memory_repo.end_session(session_id))

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
