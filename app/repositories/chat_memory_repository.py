import uuid
from datetime import datetime
from typing import Any

from app.core.config import config
from app.core.mongodb import get_chat_collection


class ChatMemoryRepository:
    def __init__(self):
        self.collection = get_chat_collection()

    async def save_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        question_type: str = "일반",
        risk_level: str = "Normal",
    ) -> str:
        """메시지를 MongoDB에 저장"""
        message_doc = {
            "_id": str(uuid.uuid4()),
            "session_id": session_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "question_type": question_type,
            "risk_level": risk_level,
            "created_at": datetime.utcnow(),
            "is_deleted": False,
        }

        await self.collection.insert_one(message_doc)
        return str(message_doc["_id"])

    async def get_recent_messages(
        self, session_id: str, user_id: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """세션의 최근 메시지들을 조회 (소유자 검증 포함)"""
        if limit is None:
            limit = config.CHAT_HISTORY_LIMIT

        cursor = (
            self.collection.find({"session_id": session_id, "user_id": user_id, "is_deleted": False})
            .sort("created_at", -1)
            .limit(limit)
        )

        messages = await cursor.to_list(length=limit)
        return list(reversed(messages))  # 시간순 정렬

    async def end_session(self, session_id: str) -> bool:
        """세션 종료 (soft delete)"""
        result = await self.collection.update_many({"session_id": session_id}, {"$set": {"is_deleted": True}})
        return bool(result.modified_count > 0)

    async def verify_session_owner(self, session_id: str, user_id: str) -> bool:
        """세션 소유자 검증"""
        message = await self.collection.find_one({"session_id": session_id, "user_id": user_id, "is_deleted": False})
        return message is not None

    async def get_recent_messages_for_history(
        self, session_id: str, user_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """히스토리 전용 메시지 조회 (더 많은 메시지 반환)"""
        cursor = (
            self.collection.find({"session_id": session_id, "user_id": user_id, "is_deleted": False})
            .sort("created_at", 1)
            .limit(limit)
        )  # 시간순 정렬

        messages = await cursor.to_list(length=limit)
        return list(messages)

    def create_session_id(self) -> str:
        """새로운 세션 ID 생성"""
        return f"chat_{uuid.uuid4().hex[:12]}"
