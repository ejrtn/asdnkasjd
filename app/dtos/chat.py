from pydantic import BaseModel, Field


# ==========================================
# [추가된 기능] 필수 2: 실시간 챗봇
# ==========================================
class ChatMessage(BaseModel):
    role: str = Field(..., description="system, user, assistant 중 하나")
    content: str = Field(..., description="대화 내용")


class ChatRequest(BaseModel):
    user_id: str = Field(..., description="사용자 ID (이메일)")
    session_id: str | None = Field(None, description="대화 세션 ID (없으면 신규 생성)")
    messages: list[ChatMessage] = Field(..., description="이전 대화 맥락을 포함한 메시지 목록")


class ChatResponse(BaseModel):
    session_id: str = Field(..., description="대화 세션 ID")
    question_type: str = Field(..., description="질문 분류 (복약/증상/일반/시스템)")
    risk_level: str = Field(..., description="위험도 (Normal/Emergency)")
    reply: str = Field(..., description="챗봇(LLM)의 실시간 응답 내용")
    multimodal_assets: list[dict] | None = Field(None, description="생성된 카드뉴스/이미지/음성(TTS) 등 에셋 정보")


class ChatSessionResponse(BaseModel):
    session_id: str
    last_message: str
    created_at: str


class ChatMessageRequest(BaseModel):
    message: str = Field(..., description="사용자 메시지")
    session_id: str | None = Field(None, description="세션 ID (없으면 신규 생성)")


class ChatMessageResponse(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    assistant_message: str = Field(..., description="챗봇 응답")
    risk_level: str = Field(..., description="위험도 (Normal/Emergency)")
    question_type: str = Field(..., description="질문 분류 (복약/증상/일반)")


class ChatEndRequest(BaseModel):
    session_id: str = Field(..., description="종료할 세션 ID")
