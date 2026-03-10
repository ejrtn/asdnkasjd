from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import config


class MongoDB:
    client: AsyncIOMotorClient | None = None
    database: AsyncIOMotorDatabase | None = None


mongodb = MongoDB()


async def connect_to_mongo():
    """MongoDB 연결 초기화 및 연결 테스트"""
    mongodb.client = AsyncIOMotorClient(config.MONGODB_URI)
    # 실제 연결 테스트
    await mongodb.client.admin.command("ping")
    mongodb.database = mongodb.client[config.MONGODB_DB_NAME]


async def close_mongo_connection():
    """MongoDB 연결 종료"""
    if mongodb.client:
        mongodb.client.close()


def get_database() -> AsyncIOMotorDatabase:
    """MongoDB 데이터베이스 객체 반환"""
    if mongodb.database is None:
        raise RuntimeError("MongoDB is not connected. Please check connection.")
    return mongodb.database


def get_chat_collection():
    """채팅 메시지 컬렉션 반환"""
    if mongodb.database is None:
        raise RuntimeError("MongoDB is not connected. Please check connection.")
    return mongodb.database[config.MONGODB_CHAT_COLLECTION]
