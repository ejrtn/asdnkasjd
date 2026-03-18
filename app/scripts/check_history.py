import asyncio

from tortoise import Tortoise

from app.core.config import config
from app.models.user import User
from app.services.upload import UploadService


async def main():
    await Tortoise.init(
        db_url=f"mysql://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}",
        modules={
            "models": [
                "app.models.prescription",
                "app.models.user",
                "app.models.prescription_drug",
                "app.models.current_med",
                "app.models.upload",
                "app.models.health_profile",
                "app.models.pill_recognitions",
                "app.models.allergy",
                "app.models.blood_pressure_record",
                "app.models.blood_sugar_record",
                "app.models.chronic_disease",
                "app.models.alarm",
                "app.models.chat_message",
                "app.models.ocr_history",
                "app.models.plan_check_list",
                "app.models.llm_life_guide",
            ]
        },
    )

    user = await User.first()
    if user:
        service = UploadService()
        history = await service.get_upload_history(user)
        import json

        print(json.dumps(history, indent=2, ensure_ascii=False))

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
