from fastapi import FastAPI
from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise

from app.core import config

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
    "app.models.pill_recognitions",
    "app.models.system_log",
    "app.models.upload",
    "app.models.ocr_history",
    "app.models.blood_pressure_record",
    "app.models.blood_sugar_record",
    "app.models.health_profile",
    "app.models.plan_check_list",
    "app.models.drug_master",
    "app.models.drug_master_tmp",
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
    "use_tz": True,
    "timezone": "UTC",
}


def initialize_tortoise(app: FastAPI) -> None:
    """
    FastAPI 애플리케이션에 Tortoise-ORM 설정을 등록하고 초기화합니다.
    """
    Tortoise.init_models(TORTOISE_APP_MODELS, "models")

    # DB 연결 실패 시 SQLite로 폴백하는 로직 추가 (데모용)
    try:
        register_tortoise(
            app,
            config=TORTOISE_ORM,
            generate_schemas=False,
            add_exception_handlers=True,
        )
    except Exception as e:
        print(f"MySQL connection failed: {e}. Falling back to in-memory SQLite for demo.")
        sqlite_orm = {
            "connections": {"default": "sqlite://:memory:"},
            "apps": {"models": {"models": TORTOISE_APP_MODELS}},
            "use_tz": True,
            "timezone": "UTC",
        }
        register_tortoise(
            app,
            config=sqlite_orm,
            generate_schemas=True,
            add_exception_handlers=True,
        )
