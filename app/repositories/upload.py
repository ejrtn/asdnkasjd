from datetime import datetime, timedelta

from app.models.upload import Upload


class UploadRepository:
    """
    User 모델에 대한 데이터베이스 접근 및 CRUD 연산을 담당하는 레포지토리 클래스입니다.
    """

    def __init__(self):
        self._model = Upload

    async def create_file(self, user_id: str, uploads: list[dict]):
        """
        여러 개의 복용 약물 정보를 한꺼번에 생성합니다.
        """

        objs = [self._model(user_id=user_id, **data) for data in uploads]
        await self._model.bulk_create(objs)

    async def get_latest_day_uploads(self, user_id: str):
        """
        가장 최근 날짜(년-월-일)에 해당하는 하루치 업로드 데이터 목록을 반환합니다.
        """
        latest = await self._model.filter(user_id=user_id).order_by("-created_at").first()
        if not latest:
            return []

        start = datetime.combine(latest.created_at.date(), datetime.min.time())
        end = start + timedelta(days=1)

        return await self._model.filter(user_id=user_id, created_at__gte=start, created_at__lt=end).prefetch_related(
            "prescription__drugs", "pill_front_asset__back_upload", "pill_back_asset__front_upload"
        )
