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
        created_objs = []
        for data in uploads:
            obj = await self._model.create(**{**data, "user_id": user_id})
            created_objs.append(obj)
        return created_objs

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
            "prescription__drugs", "pill_recognitions_front", "pill_recognitions_back"
        )

    async def get_all_uploads(self, user_id: str):
        """
        사용자의 모든 업로드 기록을 최신순으로 정렬하여 반환합니다.
        """
        return await self._model.filter(user_id=user_id).order_by("-created_at")

    async def delete_upload(self, upload_id: int, user_id: str) -> bool:
        """
        주어진 upload_id 업로드 레코드를 삭제합니다.
        사용자가 자신의 파일만 삭제할 수 있도록 user_id 조건을 부고, 삭제 성공 시 True 반환.
        """
        deleted_count = await self._model.filter(id=upload_id, user_id=user_id).delete()
        return bool(deleted_count > 0)

    async def get_upload_by_id_with_relations(self, upload_id: int, user_id: str):
        """
        특정 업로드 ID에 대해 연관된 분석 결과(처방전, 알약 등)를 함께 로드하여 반환합니다.
        """
        return (
            await self._model.filter(id=upload_id, user_id=user_id)
            .prefetch_related("prescription__drugs", "pill_recognitions_front", "pill_recognitions_back")
            .first()
        )
