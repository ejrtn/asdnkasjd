from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.security import get_request_user
from app.dtos.chat import ChatEndRequest, ChatMessage, ChatMessageRequest, ChatMessageResponse, ChatRequest
from app.models.user import User
from app.services.chat import ChatService

chat_router = APIRouter(prefix="/chat", tags=["chat"])


@chat_router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(
    request: ChatMessageRequest,
) -> ChatMessageResponse:
    """
    [CHAT] 챗봇 메시지 전송(세션 유지) - 비로그인 상태에서도 사용 가능.
    """
    chat_service = ChatService()

    chat_request = ChatRequest(
        user_id="guest",
        session_id=request.session_id,
        messages=[ChatMessage(role="user", content=request.message)],
    )

    response = await chat_service.process_chat(chat_request)

    return ChatMessageResponse(
        session_id=response.session_id,
        assistant_message=response.reply,
        risk_level=response.risk_level,
        question_type=response.question_type,
    )


@chat_router.post("/end")
async def end_chat(
    request: ChatEndRequest,
    user: Annotated[User, Depends(get_request_user)],
) -> dict:
    """
    [CHAT] 채팅 종료(대화 내용 초기화).
    """
    # TODO: 세션 종료 로직 구현
    return {"detail": "채팅이 종료되었습니다.", "session_id": request.session_id}
