import asyncio

from tortoise import Tortoise

from app.db.databases import TORTOISE_ORM
from app.models.user import User
from app.repositories.upload import UploadRepository


async def run_debug():
    # DB 초기화
    await Tortoise.init(config=TORTOISE_ORM)

    # 임의의 사용자 ID (필요시 DB에서 가져오거나 생성)
    user = await User.all().first()
    if not user:
        print("사용자가 없습니다.")
        return

    user_id = user.id
    repo = UploadRepository()

    try:
        print(f"--- '{user_id}' 사용자의 최근 업로드 데이터 조회 테스트 ---")
        results = await repo.get_latest_day_uploads(user_id)
        print(f"조회 결과 수: {len(results)}")
        for r in results:
            print(f"- {r.file_path} (ID: {r.id}, Created At: {r.created_at})")
            # Prefetch 확인
            try:
                if hasattr(r, "prescription") and r.prescription:
                    print(f"  [Prescription] Drugs count: {len(r.prescription.drugs)}")
                if hasattr(r, "pill_front_asset") and r.pill_front_asset:
                    print(f"  [Pill Front] {r.pill_front_asset.pill_name}")
                if hasattr(r, "pill_back_asset") and r.pill_back_asset:
                    print(f"  [Pill Back] {r.pill_back_asset.pill_name}")
            except Exception as e:
                print(f"  [Prefetch Error] {e}")

    except Exception:
        print("!!! Error occurred !!!")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_debug())
