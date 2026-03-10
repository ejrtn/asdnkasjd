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
