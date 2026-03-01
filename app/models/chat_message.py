from tortoise import fields, models


class ChatMessage(models.Model):
    """
    사용자와 챗봇 간의 대화 메시지 이력을 관리하는 모델입니다.
    세션별로 대화가 구분되며, 응답 생성 시 참고한 건강 가이드 정보를 연결합니다.
    """

    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="chat_messages")
    session_id = fields.CharField(max_length=100)  # 대화 세션 묶음
    role = fields.CharField(max_length=20)  # user 또는 ai
    message = fields.TextField()
    # [RAG 핵심] 질문 시 참고한 가이드 ID를 연결하여 맥락 유지
    reference_guide = fields.ForeignKeyField("models.LLMLifeGuide", related_name="chats", null=True)
    is_deleted = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chat_messages"
