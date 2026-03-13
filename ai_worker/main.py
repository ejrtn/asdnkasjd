import asyncio
import logging
import os
import signal
import sys

from tortoise import Tortoise

from ai_worker.tasks.alarm_scheduler import run_alarm_scheduler

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)

# 환경변수에서 DB 설정 가져오기
DB_URL = os.getenv("DATABASE_URL", "mysql://ozcoding:pw1234@mysql:3306/ai_health?charset=utf8mb4")

MODELS = [
    "app.models.alarm",
    "app.models.alarm_history",
    "app.models.allergy",
    "app.models.blood_pressure_record",
    "app.models.blood_sugar_record",
    "app.models.chat_message",
    "app.models.chronic_disease",
    "app.models.current_med",
    "app.models.health_profile",
    "app.models.llm_life_guide",
    "app.models.multimodal_asset",
    "app.models.ocr_history",
    "app.models.pill_recognitions",
    "app.models.prescription",
    "app.models.prescription_drug",
    "app.models.system_log",
    "app.models.upload",
    "app.models.user",
]

# 전역 변수로 스케줄러 태스크 관리
scheduler_task: asyncio.Task | None = None


def signal_handler(signum: int, frame) -> None:
    """시그널 핸들러 - graceful shutdown"""
    logger.info(f"Signal {signum} received, shutting down gracefully...")
    if scheduler_task and not scheduler_task.done():
        scheduler_task.cancel()


async def main() -> None:
    global scheduler_task

    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logger.info("🔥 AI Worker started")
        logger.info(f"🗄️ Worker DB_URL = {DB_URL}")

        # DB 연결
        await Tortoise.init(
            db_url=DB_URL,
            modules={"models": MODELS},
        )
        logger.info("✅ DB 연결 완료")

        # 알람 스케줄러 시작
        logger.info("⏰ 알람 스케줄러 시작")
        scheduler_task = asyncio.create_task(run_alarm_scheduler())
        await scheduler_task

    except asyncio.CancelledError:
        logger.info("⏹️ 스케줄러가 취소되었습니다")
    except Exception as e:
        logger.error(f"❌ AI Worker 실행 중 오류 발생: {e}")
        raise
    finally:
        # 리소스 정리
        logger.info("🧹 리소스 정리 중...")
        await Tortoise.close_connections()
        logger.info("👋 AI Worker 종료")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 사용자에 의해 종료됨")
    except Exception as e:
        logger.error(f"❌ 치명적 오류: {e}")
        sys.exit(1)
