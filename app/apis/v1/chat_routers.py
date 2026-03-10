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
    user: Annotated[User, Depends(get_request_user)],
) -> ChatMessageResponse:
    """
    [CHAT] 챗봇 메시지 전송(세션 유지) - 로그인 필수.
    """
    chat_service = ChatService()

    chat_request = ChatRequest(
        user_id=user.id,
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
    [CHAT] 채팅 종료(대화 내용 초기화) - 로그인 필수.
    """
    chat_service = ChatService()
    success = await chat_service.end_chat_session(request.session_id, user.id)

    if success:
        return {"detail": "채팅이 종료되었습니다.", "session_id": request.session_id}
    else:
        return {"detail": "세션을 찾을 수 없거나 권한이 없습니다.", "session_id": request.session_id}


@chat_router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str,
    user: Annotated[User, Depends(get_request_user)],
) -> dict:
    """
    [CHAT] 채팅 대화 내역 조회 - 로그인 필수.
    """
    chat_service = ChatService()
    messages = await chat_service.get_chat_history(session_id=session_id, user_id=user.id)
    return {"session_id": session_id, "messages": messages}
