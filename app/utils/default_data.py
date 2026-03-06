import random
from datetime import date, datetime, time, timedelta
from typing import cast

from app.models.alarm import Alarm
from app.models.alarm_history import AlarmHistory
from app.models.allergy import Allergy
from app.models.blood_pressure_record import BloodPressureRecord, RecordTime
from app.models.blood_sugar_record import BloodSugarRecord, GlucoseMeasureType
from app.models.chat_message import ChatMessage
from app.models.chronic_disease import ChronicDisease
from app.models.cnn_history import CNNHistory
from app.models.current_med import AddedFrom, CurrentMed, DoseTime
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
        """
        애플리케이션 초기화 시 필요한 기본 데이터를 생성하는 메인 메서드입니다.
        """
        print("create_default_data")
        # 사용자 목록 및 기본 정보 풀
        users_info = [
            {
                "id": "ejrtn153@naver.com",
                "name": "홍길동",
                "nickname": "길동이",
                "birthday": "1990-01-01",
                "gender": "남자",
                "pills": 5,
                "diseases": 2,
                "allergy": 1,
            },
            {
                "id": "ejrtn153@gmail.com",
                "name": "김철수",
                "nickname": "철수",
                "birthday": "1985-05-15",
                "gender": "남자",
                "pills": 2,
                "diseases": 1,
                "allergy": 0,
            },
            {
                "id": "leehaean1009@gmail.com",
                "name": "이해안",
                "nickname": "해안이",
                "birthday": "1992-10-09",
                "gender": "여자",
                "pills": 4,
                "diseases": 3,
                "allergy": 1,
            },
            {
                "id": "keyhijmik@gmail.com",
                "name": "강희제",
                "nickname": "희제",
                "birthday": "1988-03-20",
                "gender": "남자",
                "pills": 1,
                "diseases": 0,
                "allergy": 1,
            },
            {
                "id": "gina6545@gmail.com",
                "name": "박지나",
                "nickname": "지나",
                "birthday": "1995-12-25",
                "gender": "여자",
                "pills": 3,
                "diseases": 2,
                "allergy": 0,
            },
        ]

        pill_pool = [
            {
                "name": "타이레놀정 500mg",
                "dose": "500mg",
                "count": "1정",
                "freq": "3회",
                "time": DoseTime.LUNCH,
                "from": AddedFrom.HOSPITAL,
            },
            {
                "name": "메트포르민 500mg",
                "dose": "500mg",
                "count": "1정",
                "freq": "2회",
                "time": DoseTime.MORNING,
                "from": AddedFrom.PHARMACY,
            },
            {
                "name": "아모디핀정 5mg",
                "dose": "5mg",
                "count": "1정",
                "freq": "1회",
                "time": DoseTime.MORNING,
                "from": AddedFrom.UNKNOWN,
            },
            {
                "name": "고지혈정 10mg",
                "dose": "10mg",
                "count": "1정",
                "freq": "1회",
                "time": DoseTime.MORNING,
                "from": AddedFrom.PHARMACY,
            },
            {
                "name": "비타민C 1000mg",
                "dose": "1000mg",
                "count": "1정",
                "freq": "1회",
                "time": DoseTime.DINNER,
                "from": AddedFrom.UNKNOWN,
            },
        ]

        disease_pool = [
            {"name": "고혈압", "when": "10년 이상"},
            {"name": "당뇨병", "when": "5년 이내"},
            {"name": "고지혈증", "when": "알수없음"},
            {"name": "천식", "when": "1년 이내"},
        ]

        allergy_pool = [
            {"allergy_type": "기타", "allergy_name": "꽃가루", "symptom": "두드러기, 가려움증"},
            {"allergy_type": "기타", "allergy_name": "먼지", "symptom": "재채기, 콧물"},
            {"allergy_type": "기타", "allergy_name": "고양이 털", "symptom": "호흡곤란, 부종"},
        ]

        for uinfo in users_info:
            user = await self._create_user(uinfo)
            clinical_data = await self._create_clinical_data(user, uinfo, pill_pool, disease_pool, allergy_pool)
            await self._create_lifestyle_data(user, clinical_data)
            await self._create_service_data(user, uinfo, clinical_data)

        print("Default data population for multiple users completed successfully.")

    async def _create_user(self, uinfo: dict) -> User:
        user_data = {
            "id": uinfo["id"],
            "password": hash_password("!Qq123456789"),
            "name": uinfo["name"],
            "nickname": uinfo["nickname"],
            "birthday": uinfo["birthday"],
            "gender": uinfo["gender"],
            "phone_number": f"010{abs(hash(uinfo['id'])) % 100000000:08d}",
            "alarm_tf": True,
            "is_terms_agreed": True,
            "is_privacy_agreed": True,
            "is_marketing_agreed": True,
            "is_alarm_agreed": True,
        }
        user: User
        user, created = await User.get_or_create(id=user_data["id"], defaults=user_data)
        if not created:
            print(f"User {user.id} already exists.")

        return cast(User, user)

    async def _create_clinical_data(
        self, user: User, uinfo: dict, pill_pool: list, disease_pool: list, allergy_pool: list
    ) -> dict:
        # 알레르기 생성
        if uinfo["allergy"] > 0:
            a_idx = abs(hash(user.id)) % len(allergy_pool)
            a = allergy_pool[a_idx]
            print(a)
            await Allergy.get_or_create(
                user=user,
                allergy_type=a["allergy_type"],
                allergy_name=a["allergy_name"],
                symptom=a["symptom"],
            )

        # 만성질환 생성
        for i in range(uinfo["diseases"]):
            d = disease_pool[i % len(disease_pool)]
            await ChronicDisease.get_or_create(
                user=user, disease_name=d["name"], defaults={"when_to_diagnose": d["when"]}
            )

        # 현재 복용 약물 및 알람 생성
        meds = []
        for i in range(uinfo["pills"]):
            p = pill_pool[i % len(pill_pool)]
            current_med, _ = await CurrentMed.get_or_create(
                user=user,
                medication_name=p["name"],
                defaults={
                    "one_dose": p["dose"],
                    "daily_dose_count": p["freq"],
                    "one_dose_count": p["count"],
                    "dose_time": p["time"],
                    "added_from": p["from"],
                    "start_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m"),
                },
            )
            meds.append(current_med)

            # 첫 번째 약물에 대해서만 알람 생성
            if i == 0:
                alarm, _ = await Alarm.get_or_create(
                    current_med=current_med, user=user, defaults={"alarm_time": time(9, 0, 0), "is_active": True}
                )
                await AlarmHistory.get_or_create(alarm=alarm, defaults={"is_confirmed": True})

        return {"meds": meds}

    async def _create_lifestyle_data(self, user: User, clinical_data: dict):
        hp_hash = abs(hash(user.id))
        health_profile_defaults = {
            "family_history": FamilyHistory.MAN if hp_hash % 2 == 0 else FamilyHistory.NO,
            "family_history_note": "암",
            "height_cm": 160.0 + (hp_hash % 20),
            "weight_kg": 50.0 + (hp_hash % 30),
            "weight_change": WeightChange.NO_CHANGE,
            "sleep_hours": 7.0,
            "sleep_change": SleepChange.NO_CHANGE,
            "smoking_status": SmokingStatus.NEVER,
            "smoking_years": 10,
            "smoking_per_week": 1,
            "drinking_status": DrinkingStatus.NEVER,
            "drinking_years": 5,
            "drinking_per_week": 1,
            "exercise_frequency": ExerciseFrequency.WEEK_3_OR_MORE,
            "diet_type": DietType.BALANCED,
        }
        hp, created = await HealthProfile.get_or_create(user=user, defaults=health_profile_defaults)
        if not created:
            await hp.update_from_dict(health_profile_defaults).save()

        # 혈압 기록 (히스토리 생성)
        base_time = datetime.now()
        bp_records = []

        for i in range(30):
            # i가 커질수록 12시간씩 과거로 감
            past_time = base_time - timedelta(hours=i * 12)

            bp_records.append(
                {
                    "systolic": 120 + random.randint(-5, 15),
                    "diastolic": 75 + random.randint(-5, 10),
                    "pulse": 70 + random.randint(-5, 15),
                    "measure_type": RecordTime.MORNING if i % 2 == 0 else RecordTime.RANDOM,
                    "created_at": past_time.isoformat(),  # 이 값을 프론트로 보냄
                }
            )
        print(bp_records)
        if await BloodPressureRecord.filter(user=user).count() == 0:
            for bp in bp_records:
                await BloodPressureRecord.create(user=user, **bp)

        # 혈당 기록 (히스토리 생성)
        # 현재 시간 기준
        base_time = datetime.now()
        bs_records = []

        for i in range(15):
            # 날짜를 하루씩 뒤로 감
            current_date = base_time - timedelta(days=i)

            # 1. 아침 공복 (오전 7~8시경)
            fasting_time = current_date.replace(hour=7, minute=random.randint(0, 59))
            bs_records.append(
                {
                    "glucose_mg_dl": float(95 + random.randint(-15, 15)),  # 80~110 범위
                    "measure_type": GlucoseMeasureType.FASTING,
                    "created_at": fasting_time.isoformat(),
                }
            )

            # 2. 식후 2시간 (오후 1~2시경)
            after_meal_time = current_date.replace(hour=13, minute=random.randint(0, 59))
            bs_records.append(
                {
                    "glucose_mg_dl": float(140 + random.randint(-20, 30)),  # 120~170 범위
                    "measure_type": GlucoseMeasureType.AFTER_MEAL,
                    "created_at": after_meal_time.isoformat(),
                }
            )
        if await BloodSugarRecord.filter(user=user).count() == 0:
            for bs in bs_records:
                await BloodSugarRecord.create(user=user, **bs)

    async def _create_service_data(self, user: User, uinfo: dict, clinical_data: dict):
        # 업로드 어셋
        presc_upload, _ = await Upload.get_or_create(
            user=user, file_path="/static/prescription_sample.png", file_type="png", category="prescription"
        )
        upload_front, _ = await Upload.get_or_create(
            user=user, file_path="/static/pill_front.png", file_type="png", category="pill_front"
        )
        upload_back, _ = await Upload.get_or_create(
            user=user, file_path="/static/pill_back.png", file_type="png", category="pill_back"
        )

        # 처방전
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

        # 처방전 OCR History
        await OCRHistory.get_or_create(
            user=user,
            front_upload=presc_upload,
            defaults={
                "raw_text": f"처방전\n환자 성명: {uinfo['name']}\n의료기관: 서울대학교병원\n처방 의약품: 아모디핀정 5mg\n투약량: 1정\n투여횟수: 1일 1회\n투약일수: 30일",
                "is_valid": True,
                "inference_metadata": {"time_spent": 1500, "model": "clova_ocr"},
            },
        )

        # AI 가이드
        guide, _ = await LLMLifeGuide.get_or_create(
            user=user,
            guide_type="복약주의",
            defaults={
                "user_current_status": f"{uinfo['name']}님 맞춤형 상태",
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

        # 채팅
        await ChatMessage.get_or_create(
            session_id=f"session_{user.id[:5]}",
            role="ai",
            message=f"안녕하세요 {uinfo['nickname']}님! 무엇을 도와드릴까요?",
            user=user,
        )

        # 알약 식별
        cnn_history, _ = await CNNHistory.get_or_create(
            user=user,
            front_upload=upload_front,
            back_upload=upload_back,
            defaults={
                "model_version": "gpt-4o-mini",
                "confidence": 0.95,
                "raw_result": {"모양": "장방형", "색상": "흰색"},
            },
        )
        # 과거 OCR History 데이터 (더미)
        ocr_texts = ["AMLO 5", "METFO 500", "LIPITOR 10"]
        for i, text in enumerate(ocr_texts):
            past_front, _ = await Upload.get_or_create(
                user=user, file_path=f"/static/past_front_{i}.png", file_type="png", category="pill_front"
            )
            past_back, _ = await Upload.get_or_create(
                user=user, file_path=f"/static/past_back_{i}.png", file_type="png", category="pill_back"
            )
            await OCRHistory.get_or_create(
                user=user,
                front_upload=past_front,
                back_upload=past_back,
                defaults={
                    "raw_text": text,
                    "is_valid": True,
                    "inference_metadata": {"time_spent": random.randint(200, 800), "model": "tesseract"},
                },
            )

        ocr_history, _ = await OCRHistory.get_or_create(
            user=user,
            front_upload=upload_front,
            back_upload=upload_back,
            defaults={"raw_text": "TYLENOL 500", "is_valid": True},
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
