from fastapi import FastAPI
from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise

from app.core import config
from app.core.config import Env
from app.utils.default_data import DefaultData

TORTOISE_APP_MODELS = [
    "aerich.models",
    "app.models.user",
    "app.models.alarm",
    "app.models.alarm_history",
    "app.models.allergy",
    "app.models.chat_message",
    "app.models.chronic_disease",
    "app.models.current_med",
    "app.models.llm_life_guide",
    "app.models.multimodal_asset",
    "app.models.prescription",
    "app.models.prescription_drug",
    "app.models.pill_recognition",
    "app.models.system_log",
    "app.models.upload",
    "app.models.ocr_history",
    "app.models.cnn_history",
]

TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.mysql",
            "dialect": "asyncmy",
            "credentials": {
                "host": config.DB_HOST,
                "port": config.DB_PORT,
                "user": config.DB_USER,
                "password": config.DB_PASSWORD,
                "database": config.DB_NAME,
                "connect_timeout": config.DB_CONNECT_TIMEOUT,
                "maxsize": config.DB_CONNECTION_POOL_MAXSIZE,
            },
        },
    },
    "apps": {
        "models": {
            "models": TORTOISE_APP_MODELS,
        },
    },
    "timezone": "Asia/Seoul",
}


def initialize_tortoise(app: FastAPI) -> None:
    """
    FastAPI 애플리케이션에 Tortoise-ORM 설정을 등록하고 초기화합니다.

    Args:
        app (FastAPI): 초기화할 FastAPI 인스턴스
    """
    Tortoise.init_models(TORTOISE_APP_MODELS, "models")

    # 여기서 generate_schemas=False로 두고, startup에서만 제어합니다.
    register_tortoise(app, config=TORTOISE_ORM, generate_schemas=False, add_exception_handlers=True)

    @app.on_event("startup")
    async def on_startup():
        """
        애플리케이션 시작 시 실행되는 이벤트 핸들러입니다.
        로컬 환경일 경우 기존 테이블을 모두 삭제하고 스키마를 새로 생성하여 개발 편의성을 제공합니다.
        """
        if config.ENV == Env.LOCAL:
            print(f"Current Environment: {config.ENV}. Resetting database...")

            # 1. DB 연결 객체 가져오기
            conn = Tortoise.get_connection("default")

            # 2. 외래 키 체크 비활성화 (MySQL에서 테이블을 순서 상관없이 지우기 위해 필수)
            await conn.execute_query("SET FOREIGN_KEY_CHECKS = 0;")

            try:
                # 3. Tortoise에 등록된 모든 모델의 테이블을 순회하며 DROP
                for _app_name, models in Tortoise.apps.items():
                    for _model_name, model_obj in models.items():
                        table_name = model_obj._meta.db_table
                        print(f"Dropping table: {table_name}")
                        await conn.execute_query(f"DROP TABLE IF EXISTS `{table_name}`;")

                # 4. Aerich 마이그레이션 테이블도 명시적으로 삭제
                await conn.execute_query("DROP TABLE IF EXISTS `aerich`;")

                print("All tables dropped. Re-generating schemas...")

                # 5. 스키마 새로 생성
                await Tortoise.generate_schemas(safe=False)
                print("Database schemas re-generated successfully.")

                # --- [추가된 부분: 초기 데이터 실행] ---
                default_data = DefaultData()
                await default_data.create_default_data()

            finally:
                # 6. 외래 키 체크 다시 활성화
                await conn.execute_query("SET FOREIGN_KEY_CHECKS = 1;")
