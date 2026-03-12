import random
from datetime import datetime, time, timedelta
from typing import cast

from app.models.alarm import Alarm
from app.models.alarm_history import AlarmHistory
from app.models.allergy import Allergy
from app.models.blood_pressure_record import BloodPressureRecord, RecordTime
from app.models.blood_sugar_record import BloodSugarRecord, GlucoseMeasureType
from app.models.chat_message import ChatMessage
from app.models.chronic_disease import ChronicDisease
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
from app.models.pill_recognitions import PillRecognition

# Removed app.models.pill_recognition import
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

        for i in range(15):
            # i가 커질수록 12시간씩 과거로 감
            past_time = base_time - timedelta(hours=i * 12)

            bp_records.append(
                {
                    "systolic": 120 + random.randint(-5, 15),
                    "diastolic": 75 + random.randint(-5, 10),
                    "pulse": 70 + random.randint(-5, 15),
                    "measure_type": RecordTime.MORNING if i % 2 == 0 else RecordTime.DINNER,
                    "created_at": past_time.isoformat(),  # 이 값을 프론트로 보냄
                }
            )

        print(bp_records)
        if await BloodPressureRecord.filter(user=user).count() == 0:
            for bp in bp_records:
                bp_record = BloodPressureRecord(user=user, **bp)
                await bp_record.save()

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

            # 2. 취침 전
            last_time = current_date.replace(hour=22, minute=random.randint(0, 59))
            bs_records.append(
                {
                    "glucose_mg_dl": float(100 + random.randint(-20, 30)),  # 120~170 범위
                    "measure_type": GlucoseMeasureType.BEDTIME,
                    "created_at": last_time.isoformat(),
                }
            )
        if await BloodSugarRecord.filter(user=user).count() == 0:
            for bs in bs_records:
                bs_record = BloodSugarRecord(user=user, **bs)
                await bs_record.save()

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

        # AI 가이드
        guide, _ = await LLMLifeGuide.get_or_create(
            user=user,
            defaults={
                "user_current_status": """
                    신중하고 전문적인 의료 도우미로서, 아래 환자의 건강 상태를 바탕으로 '생활 안내 가이드'를 작성해줘.

                        [환자 상태]
                        - 만성 질환: 고혈압, 당뇨병
                        - 알레르기: 꽃가루
                        - 현재 복용 약: 타이레놀정 500mg, 메트포르민 500mg, 아모디핀정 5mg, 고지혈정 10mg, 비타민C 1000mg
                        - 최근 혈압 기록: 115/85 mmHg
                        - 최근 혈당 기록: 89.0 mg/dL (취침 전)

                        [참고 문서]
                        당뇨병 환자는 규칙적인 식사와 혈당 관리가 중요합니다.
                    단순당이 많은 음식은 줄이고, 식이섬유가 풍부한 식사를 권장합니다.
                    운동은 혈당 조절에 도움이 되지만, 저혈당 위험이 있는 경우 주의해야 합니다.


                    고혈압 환자는 나트륨 섭취를 줄이는 것이 중요합니다.
                    국물 음식, 젓갈, 가공식품 섭취를 줄이는 것이 좋습니다.
                    규칙적인 유산소 운동은 혈압 조절에 도움이 됩니다.
                    과도한 음주는 혈압 상승에 영향을 줄 수 있어 주의가 필요합니다.


                    저염식은 고혈압 관리에 도움이 됩니다.
                    국, 찌개, 라면, 햄, 소시지 등 나트륨이 많은 음식은 줄이는 것이 좋습니다.
                    음식을 조리할 때 소금과 간장 사용을 줄이고, 천연 재료의 맛을 살리는 방법이 권장됩니다.


                        [작성 가이드라인]
                        1. 과한 확정 진단(예: ~병입니다)은 피하고, '권장합니다', '주의가 필요합니다' 등의 조언 톤을 유지할 것.
                        2. 약물 상호작용 및 알레르기 성분을 최우선으로 체크할 것.
                        3. 반드시 아래의 JSON 구조로 응답할 것.
                        4. 만성 질환이 2개 이상이면 disease_guides를 질환 개수만큼 반드시 생성할 것(누락 금지).
                        5. disease_guides의 name은 입력된 만성 질환명(disease_list)에 있는 문자열을 그대로 사용할 것.
                        6. 참고 문서의 내용을 우선 반영하여 생활습관 및 복약 안내를 작성할 것.

                        [응답 JSON 구조]
                        {
                        "section1": {
                            "title": "복약 안전성 및 주의사항",
                            "status": "상호작용 없음 | 주의 필요 | 위험 가능성",
                            "content": "상태에 따른 상세 설명 문구",
                            "general_cautions": ["주의사항 1", "주의사항 2"]
                        },
                        "section2": {
                            "title": "질환 기반 생활습관 가이드",
                            "disease_guides": [
                            { "name": "질환명", "tips": ["가이드 1", "가이드 2"] }
                            ],
                            "integrated_point": "종합 관리 포인트 문구"
                        },
                        "section3": {
                            "title": "오늘의 실행 플랜",
                            "checklist": ["체크리스트 1", "체크리스트 2", "체크리스트 3"]
                        },
                        "section4": {
                            "title": "왜 이런 가이드가 생성되었나요?",
                            "reason": "입력된 정보(질환, 약물 등)가 가이드에 어떻게 반영되었는지에 대한 설명"
                        },
                            "disclaimer": "본 서비스는 의료 진단이나 처방을 제공하지 않으며, 참고용 안내입니다."
                        }""",
                "generated_content": {
                    "section1": {
                        "title": "복약 안전성 및 주의사항",
                        "status": "주의 필요",
                        "content": "현재 복용 중인 약물 간의 상호작용은 없으나, 알레르기 반응을 피하기 위해 꽃가루에 주의해야 합니다. 또한, 복용 중인 메트포르민은 혈당 조절에 중요한 역할을 하므로 규칙적인 복용이 필요합니다.",
                        "general_cautions": [
                            "약물 복용 시 알레르기 반응에 주의하십시오.",
                            "정해진 용량을 준수하고, 의사와 상담 없이 약물 변경을 피하십시오.",
                        ],
                    },
                    "section2": {
                        "title": "질환 기반 생활습관 가이드",
                        "disease_guides": [
                            {
                                "name": "고혈압",
                                "tips": [
                                    "나트륨 섭취를 줄이고, 가공식품과 국물 음식을 피하십시오.",
                                    "규칙적인 유산소 운동을 통해 혈압을 관리하십시오.",
                                ],
                            },
                            {
                                "name": "당뇨병",
                                "tips": [
                                    "단순당이 많은 음식은 줄이고, 식이섬유가 풍부한 식사를 권장합니다.",
                                    "운동 시 저혈당 위험에 주의하며, 혈당 수치를 모니터링하십시오.",
                                ],
                            },
                        ],
                        "integrated_point": "고혈압과 당뇨병 관리 모두에 있어 식습관과 운동이 중요하며, 정기적인 혈압 및 혈당 체크가 필요합니다.",
                    },
                    "section3": {
                        "title": "오늘의 실행 플랜",
                        "checklist": [
                            "저염식 식단으로 하루 식사 계획 세우기",
                            "30분 이상 유산소 운동 계획하기",
                            "혈당 및 혈압 체크 후 기록하기",
                        ],
                    },
                    "section4": {
                        "title": "왜 이런 가이드가 생성되었나요?",
                        "reason": "환자의 만성 질환인 고혈압과 당뇨병에 대한 관리 방안을 제시하기 위해, 복용 중인 약물과 알레르기 정보를 반영하여 안전성과 생활습관 개선을 위한 조언을 포함했습니다.",
                    },
                    "disclaimer": "본 서비스는 의료 진단이나 처방을 제공하지 않으며, 참고용 안내입니다.",
                },
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
        # 과거 OCR History 데이터 (더미)
        ocr_texts = ["AMLO 5", "METFO 500", "LIPITOR 10"]
        for i, text in enumerate(ocr_texts):
            past_front, _ = await Upload.get_or_create(
                user=user, file_path=f"/static/past_{i}_front.png", file_type="png", category="pill_front"
            )
            past_back, _ = await Upload.get_or_create(
                user=user, file_path=f"/static/past_{i}_back.png", file_type="png", category="pill_back"
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
            ocr_history=ocr_history,
            front_upload=upload_front,
            back_upload=upload_back,
            defaults={
                "pill_name": "타이레놀정 500mg",
                "pill_description": "아세트아미노펜 단일 성분의 해열 진통제입니다.",
                "model_version": "gpt-4o-mini",
                "confidence": 0.95,
                "raw_result": {"모양": "장방형", "색상": "흰색"},
            },
        )
