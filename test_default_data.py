import asyncio

from tortoise import Tortoise

from app.db.databases import TORTOISE_ORM
from app.default_data import DefaultData


async def run_test():
    try:
        # 1. Tortoise 초기화
        await Tortoise.init(config=TORTOISE_ORM)

        # 2. 스키마 생성 (테스트용)
        # 주의: 기존 데이터가 삭제될 수 있으므로 운영 환경에서는 조심해야 합니다.
        # 여기서는 단순히 연결 확인용으로 generate_schemas 사용
        await Tortoise.generate_schemas(safe=True)

        # 3. 데이터 생성 실행
        print("Starting default data population...")
        await DefaultData().create_default_data()
        print("Population finished.")

    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(run_test())
