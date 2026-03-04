from datetime import date, datetime, time, timedelta

from app.models.alarm import Alarm
from app.models.alarm_history import AlarmHistory
from app.models.allergy import Allergy
from app.models.blood_pressure_record import BloodPressureRecord
from app.models.blood_sugar_record import BloodSugarRecord, GlucoseMeasureType
from app.models.chat_message import ChatMessage
from app.models.chronic_disease import ChronicDisease
from app.models.cnn_history import CNNHistory
from app.models.current_med import CurrentMed, DoseTime
from app.models.health_profile import (
    DietType,
    DrinkingStatus,
    ExerciseFrequency,
    FamilyHistory,
    HealthProfile,
    SleepChange,
    SmokingStatus,
    WeightChange,
)
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

        # 2. 알러지 정보 생성 (allergies) - [MODIFIED] pill_allergy, food_allergy, any_allergy, symptom 필드 사용
        await Allergy.get_or_create(
            user=user,
            pill_allergy="페니실린",
            food_allergy="갑각류",
            any_allergy="꽃가루",
            symptom="두드러기, 가려움증",
        )

        # 3. 만성질환 생성 (chronic_diseases) - [MODIFIED] when_to_diagnose 필드 추가
        await ChronicDisease.get_or_create(user=user, disease_name="고혈압", defaults={"when_to_diagnose": "10Y"})
        await ChronicDisease.get_or_create(user=user, disease_name="당뇨병", defaults={"when_to_diagnose": "5Y"})

        # 4. 현재 복용 중인 약물 생성 (current_meds) - [MODIFIED] one_dose, daily_dose_count, one_dose_count 필드 사용
        current_med, _ = await CurrentMed.get_or_create(
            user=user,
            medication_name="타이레놀정 500mg",
            defaults={
                "one_dose": "500mg",
                "daily_dose_count": "3회",
                "one_dose_count": "1정",
                "dose_time": DoseTime.LUNCH,
                "added_from": "OCR",
                "start_date": "2026-03-01",
            },
        )
        current_med2, _ = await CurrentMed.get_or_create(
            user=user,
            medication_name="메트포르민 500mg",
            defaults={
                "one_dose": "500mg",
                "daily_dose_count": "2회",
                "one_dose_count": "1정",
                "dose_time": DoseTime.MORNING,
                "added_from": "MANUAL",
                "start_date": "2025-02-01",
            },
        )

        # 5. 알림 및 알림 내역 생성 (기존 유지)
        alarm, _ = await Alarm.get_or_create(
            current_med=current_med, user=user, defaults={"alarm_time": time(9, 0, 0), "is_active": True}
        )
        await AlarmHistory.get_or_create(alarm=alarm, defaults={"is_confirmed": True})

        alarm, _ = await Alarm.get_or_create(
            current_med=current_med2, user=user, defaults={"alarm_time": time(12, 0, 0), "is_active": True}
        )
        await AlarmHistory.get_or_create(alarm=alarm, defaults={"is_confirmed": True})

        # 6. 처방전 및 처방 약물 생성 (기존 유지)
        presc_upload, _ = await Upload.get_or_create(
            file_path="/static/prescription_sample.png",
            file_type="png",
            category="prescription",
            user=user,
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

        # 7. AI 가이드 및 어셋 생성 (기존 유지)
        guide, _ = await LLMLifeGuide.get_or_create(
            user=user,
            guide_type="복약주의",
            defaults={
                "user_current_status": "고혈압 및 당뇨 보유",
                "generated_content": "고혈압 약 복용 시 자몽 주스를 피하세요.",
                "is_emergency_alert": False,
            },
        )
        await MultimodalAsset.get_or_create(
            source_table="llm_life_guides",
            source_id=guide.id,
            asset_type="IMAGE_NEWS",
            defaults={"asset_url": "/static/guide_card_news.png"},
        )

        # 8. 채팅 메시지 (기존 유지)
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

        # 9. 알약 식별 이력 (기존 유지)
        upload_front, _ = await Upload.get_or_create(
            file_path="/static/pill_front.png", file_type="png", category="pill_front", user=user
        )
        upload_back, _ = await Upload.get_or_create(
            file_path="/static/pill_back.png", file_type="png", category="pill_back", user=user
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

        # 10. 건강 프로필 생성 (health_profiles) - [MODIFIED] weight_change, exercise_frequency 값 조정
        health_profile_defaults = {
            "family_history": FamilyHistory.MAN,
            "family_history_note": "고혈압",
            "height_cm": 175.5,
            "weight_kg": 72.0,
            "weight_change": WeightChange.NO_CHANGE,
            "sleep_hours": 7.0,
            "sleep_change": SleepChange.NO_CHANGE,
            "job": "개발자",
            "smoking_status": SmokingStatus.NEVER,
            "drinking_status": DrinkingStatus.CURRENT,
            "drinking_years": 5,
            "drinking_per_week": 1.5,
            "exercise_frequency": ExerciseFrequency.WEEK_3_OR_MORE,
            "diet_type": DietType.BALANCED,
        }
        hp, created = await HealthProfile.get_or_create(user=user, defaults=health_profile_defaults)
        if not created:
            # 필드 강제 업데이트 (새로 추가된 필드 반영을 위해)
            await hp.update_from_dict(health_profile_defaults).save()

        # 11. 혈압 기록 생성 (blood_pressure_records) - [MODIFIED] 더 많은 기록 추가
        bp_records = [
            {"systolic": 130, "diastolic": 85, "pulse": 80, "recorded_at": datetime.now() - timedelta(days=7)},
            {"systolic": 128, "diastolic": 82, "pulse": 78, "recorded_at": datetime.now() - timedelta(days=5)},
            {"systolic": 125, "diastolic": 80, "pulse": 75, "recorded_at": datetime.now() - timedelta(days=3)},
            {"systolic": 120, "diastolic": 80, "pulse": 72, "recorded_at": datetime.now() - timedelta(days=2)},
            {"systolic": 125, "diastolic": 82, "pulse": 75, "recorded_at": datetime.now() - timedelta(days=1)},
            {"systolic": 118, "diastolic": 78, "pulse": 70, "recorded_at": datetime.now()},
        ]
        existing_bp = await BloodPressureRecord.filter(user=user).count()

        if existing_bp == 0:
            for bp in bp_records:
                await BloodPressureRecord.create(user=user, **bp)
        else:
            print("BloodPressureRecord already exists. Skipping creation.")

        # 12. 혈당 기록 생성 (blood_sugar_records) - [MODIFIED] 더 많은 기록 추가
        bs_records = [
            {
                "glucose_mg_dl": 105.0,
                "measure_type": GlucoseMeasureType.FASTING,
                "recorded_at": datetime.now() - timedelta(days=3, hours=4),
            },
            {
                "glucose_mg_dl": 150.0,
                "measure_type": GlucoseMeasureType.AFTER_MEAL,
                "recorded_at": datetime.now() - timedelta(days=3),
            },
            {
                "glucose_mg_dl": 98.0,
                "measure_type": GlucoseMeasureType.FASTING,
                "recorded_at": datetime.now() - timedelta(days=2, hours=4),
            },
            {
                "glucose_mg_dl": 95.0,
                "measure_type": GlucoseMeasureType.FASTING,
                "recorded_at": datetime.now() - timedelta(days=1, hours=4),
            },
            {
                "glucose_mg_dl": 140.0,
                "measure_type": GlucoseMeasureType.AFTER_MEAL,
                "recorded_at": datetime.now() - timedelta(days=1),
            },
            {
                "glucose_mg_dl": 100.0,
                "measure_type": GlucoseMeasureType.FASTING,
                "recorded_at": datetime.now(),
            },
        ]
        existing_bs = await BloodSugarRecord.filter(user=user).count()

        if existing_bs == 0:
            for bs in bs_records:
                await BloodSugarRecord.create(user=user, **bs)
        else:
            print("BloodSugarRecord already exists. Skipping creation.")

        # 14. 시스템 로그 생성
        # await SystemLog.create(
        #     api_path="/api/v1/pill-scan",
        #     method="POST",
        #     response_ms=450
        # )

        print("Default data population completed successfully.")
