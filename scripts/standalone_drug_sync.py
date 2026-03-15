import asyncio
import logging
import os
import sys
from pathlib import Path

from tortoise import Tortoise

from app.core.config import config
from app.services.drug_service import DrugService

# 프로젝트 루트를 sys.path에 추가 (app 모듈을 찾기 위함)
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)  # noqa: E402

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main():
    # DB_URL 설정 (환경변수 또는 config 사용)
    db_url = os.getenv(
        "DATABASE_URL",
        f"mysql://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}?charset=utf8mb4",
    )

    models = [
        "app.models.drug_master",
        "app.models.drug_master_tmp",
    ]

    try:
        logger.info("🚀 Standalone Drug Synchronization & Enrichment Started")

        # 1. DB 연결 초기화
        await Tortoise.init(
            config={
                "connections": {"default": db_url},
                "apps": {"models": {"models": models}},
                "use_tz": True,
                "timezone": "Asia/Seoul",
            }
        )
        logger.info("✅ Database connected.")

        service = DrugService()

        # 2. 스테이징 동기화 및 LLM 보충 (batch_size 100, limit는 필요에 따라 조정)
        logger.info("Step 1: Syncing MFDS data and Batch Enriching (LLM)...")
        # limit=0 또는 큰 값을 주어 전체 보충 시도 가능
        sync_result = await service.sync_drugs(batch_size=100, auto_enrich=True, use_staging=True)
        logger.info(f"Sync Result: {sync_result}")

        # 3. 운영 테이블로 이전 (Promote)
        logger.info("Step 2: Promoting data to Production (DrugMaster)...")
        promote_result = await service.promote_tmp_to_production()
        logger.info(f"Promotion Result: {promote_result}")

        logger.info("✨ All processes completed successfully.")

    except Exception as e:
        logger.error(f"❌ Error during standalone execution: {e}")
        sys.exit(1)
    finally:
        await Tortoise.close_connections()
        logger.info("👋 Connections closed.")


if __name__ == "__main__":
    asyncio.run(main())
