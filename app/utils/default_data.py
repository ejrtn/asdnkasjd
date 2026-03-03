from datetime import date, time

from app.models.alarm import Alarm
from app.models.alarm_history import AlarmHistory
from app.models.allergy import Allergy
from app.models.chat_message import ChatMessage
from app.models.chronic_disease import ChronicDisease
from app.models.cnn_history import CNNHistory
from app.models.current_med import CurrentMed
from app.models.llm_life_guide import LLMLifeGuide
from app.models.multimodal_asset import MultimodalAsset
from app.models.ocr_history import OCRHistory
from app.models.pill_recognition import PillRecognition
from app.models.prescription import Prescription
from app.models.prescription_drug import PrescriptionDrug
from app.models.upload import Upload
from app.models.user import User
from app.utils.security import hash_password


class DefaultData:
    """
    애플리케이션 초기화 시 필요한 기본 데이터를 생성하는 클래스입니다.
    """

    async def create_default_data(self):
        # 1. 기본 사용자 생성
        user_data = {
            "id": "ejrtn153@naver.com",
            "password": hash_password("!Qq123456789"),
            "name": "홍길동",
            "nickname": "길동이",
            "birthday": "1990-01-01",
            "gender": "남자",
            "phone_number": "01012341234",
            "alarm_tf": True,
            "is_terms_agreed": True,
            "is_privacy_agreed": True,
            "is_marketing_agreed": True,
            "is_alarm_agreed": True,
        }

        user, created = await User.get_or_create(id=user_data["id"], defaults=user_data)
        if not created:
            print(f"User {user.id} already exists. Skipping creation.")

        # 2. 알러지 및 기저질환 생성
        await Allergy.get_or_create(allergy_name="갑각류 알러지", user=user)
        await ChronicDisease.get_or_create(disease_name="고혈압", user=user)

        # 3. 현재 복용 중인 약물 생성
        current_med, _ = await CurrentMed.get_or_create(
            medication_name="타이레놀정 500mg",
            user=user,
            defaults={"added_from": "PILL_SCAN", "start_date": date(2026, 3, 1)},
        )
        current_med2, _ = await CurrentMed.get_or_create(
            medication_name="메트포로민 500mg",
            user=user,
            defaults={"added_from": "PILL_SCAN", "start_date": date(2025, 2, 1)},
        )

        # 4. 알림 및 알림 내역 생성
        alarm, _ = await Alarm.get_or_create(
            current_med=current_med, user=user, defaults={"alarm_time": time(9, 0, 0), "is_active": True}
        )
        await AlarmHistory.get_or_create(alarm=alarm, defaults={"is_confirmed": True})

        alarm, _ = await Alarm.get_or_create(
            current_med=current_med2, user=user, defaults={"alarm_time": time(12, 0, 0), "is_active": True}
        )
        await AlarmHistory.get_or_create(alarm=alarm, defaults={"is_confirmed": True})

        # 5. 처방전 및 처방 약물 생성
        presc_upload, _ = await Upload.get_or_create(
            file_url="/static/prescription_sample.png", file_type="png", category="prescription", user=user
        )
        prescription, _ = await Prescription.get_or_create(
            user=user,
            upload=presc_upload,
            defaults={"hospital_name": "서울대학교병원", "prescribed_date": date(2026, 2, 20)},
        )
        await PrescriptionDrug.get_or_create(
            prescription=prescription,
            standard_drug_name="아모디핀정",
            defaults={"dosage_amount": 1.0, "daily_frequency": 1, "duration_days": 30, "is_linked_to_meds": True},
        )

        # 6. AI 가이드 생성 (채팅 및 어셋 참조용)
        guide, _ = await LLMLifeGuide.get_or_create(
            user=user,
            guide_type="복약주의",
            defaults={
                "user_current_status": "고혈압 및 갑각류 알러지 보유",
                "generated_content": "고혈압 약 복용 시 자몽 주스를 피하세요.",
                "is_emergency_alert": False,
            },
        )

        # 7. 멀티모달 어셋 생성 (카드뉴스/음성)
        await MultimodalAsset.get_or_create(
            source_table="llm_life_guides",
            source_id=guide.id,
            asset_type="IMAGE_NEWS",
            defaults={"asset_url": "/static/guide_card_news.png"},
        )

        # 8. 채팅 메시지 생성
        chat_message_data = [
            {
                "session_id": "session_001",
                "role": "ai",
                "message": "안녕하세요! Cloud9 Care 챗봇입니다. 무엇을 도와드릴까요?",
                "user": user,
                "is_deleted": False,
            },
            {
                "session_id": "session_001",
                "role": "user",
                "message": "고혈압 약 복용 시 주의사항이 있나요?",
                "user": user,
                "is_deleted": False,
            },
            {
                "session_id": "session_001",
                "role": "ai",
                "message": "네, 고혈압 약 복용 시에는 자몽 주스를 피하는 것이 좋습니다.",
                "user": user,
                "reference_guide": guide,
                "is_deleted": False,
            },
        ]

        for data in chat_message_data:
            await ChatMessage.get_or_create(**data)

        # 9. 업로드 및 AI 분석 이력 생성 (알약 식별 로직 시뮬레이션)
        upload_front, _ = await Upload.get_or_create(
            file_url="/static/pill_front.png", file_type="png", category="pill_front", user=user
        )

        upload_back, _ = await Upload.get_or_create(
            file_url="/static/pill_back.png", file_type="png", category="pill_back", user=user
        )

        cnn_history, _ = await CNNHistory.get_or_create(
            user=user,
            front_upload=upload_front,
            back_upload=upload_back,
            defaults={
                "model_version": "gpt-4o-mini",
                "confidence": 0.95,
                "raw_result": {"모양": "장방형", "색상": "흰색", "분할선": "없음", "제형": "필름코딩정제"},
            },
        )

        ocr_history, _ = await OCRHistory.get_or_create(
            user=user,
            front_upload=upload_front,
            back_upload=upload_back,
            defaults={"raw_text": "TYLENOL 500", "inference_metadata": {"latency": 150}},
        )

        # 10. 알약 식별 최종 결과 생성
        await PillRecognition.get_or_create(
            user=user,
            cnn_history=cnn_history,
            ocr_history=ocr_history,
            front_upload=upload_front,
            back_upload=upload_back,
            defaults={
                "pill_name": "타이레놀정 500mg",
                "pill_description": "아세트아미노펜 단일 성분의 해열 진통제입니다.",
                "is_linked_to_meds": True,
            },
        )

        # 11. 시스템 로그 생성
        # await SystemLog.create(
        #     api_path="/api/v1/pill-scan",
        #     method="POST",
        #     response_ms=450
        # )

        print("Default data population completed successfully.")
