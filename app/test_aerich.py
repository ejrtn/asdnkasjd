import asyncio

from aerich import Command

from app.db.databases import TORTOISE_ORM


async def run():
    command = Command(tortoise_config=TORTOISE_ORM, app="models", location="./app/db/migrations")
    await command.init()
    try:
        await command.migrate("add_repeat_days_to_alarm")
        print("Success!")
    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run())
