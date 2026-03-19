import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from openai import AsyncOpenAI

from app.core import config
from app.models.blood_pressure_record import BloodPressureRecord
from app.models.blood_sugar_record import BloodSugarRecord
from app.models.plan_check_list import PlanCheckList
from app.models.user import User
from app.repositories.llm_life_guide import LLMLifeGuideRepository

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))


def get_bp_value_class(systolic: int, diastolic: int) -> str:
    """혈압 값 상태 클래스 반환"""
    if systolic >= 140 or diastolic >= 90:
        return "danger"
    if systolic >= 120 or diastolic >= 80:
        return "caution"
    return "normal"


def get_bs_value_class(measure_type: str, glucose: float) -> str:
    """혈당 값 상태 클래스 반환"""
    if measure_type == "공복":
        if 70 <= glucose <= 100:
            return "normal"
        if 101 <= glucose <= 125:
            return "caution"
        return "danger"

    if measure_type == "식후 2시간":
        if glucose < 140:
            return "normal"
        if glucose < 200:
            return "caution"
        return "danger"

    if measure_type == "취침 전":
        if 100 <= glucose <= 140:
            return "normal"
        if 141 <= glucose <= 180:
            return "caution"
        return "danger"

    return "pending"


class DashboardService:
    def __init__(self):
        self.llm_life_guide_repo = LLMLifeGuideRepository()

    async def generate_insights(self, user: User, force_refresh: bool = False) -> dict:
        """사용자 건강 정보 기반 AI 인사이트 3개 생성"""
        try:
            # 1. 사용자 건강 데이터 수집 (병렬 실행)
            llm_life_guide, bp_records, bs_records = await asyncio.gather(
                self.llm_life_guide_repo.get_by_user_id(user_id=user.id),
                BloodPressureRecord.filter(user=user).order_by("-created_at").limit(7),
                BloodSugarRecord.filter(user=user).order_by("-created_at").limit(7),
            )

            # 2. 데이터 요약
            bp_avg = None
            if bp_records:
                systolic_avg = sum(r.systolic for r in bp_records) / len(bp_records)
                diastolic_avg = sum(r.diastolic for r in bp_records) / len(bp_records)
                bp_avg = f"{int(systolic_avg)}/{int(diastolic_avg)}"

            bs_avg = None
            if bs_records:
                bs_avg = sum(r.glucose_mg_dl for r in bs_records) / len(bs_records)

            # 3. 프롬프트 구성
            context = f"""
사용자 건강 정보:
- 건강상태: {llm_life_guide.user_current_status if llm_life_guide else "N/A"}
- 최근 7일 평균 혈압: {bp_avg or "N/A"}
- 최근 7일 평균 혈당: {f"{bs_avg:.0f}" if bs_avg else "N/A"} mg/dL

1. 위 데이터를 기반으로 짧은 건강 팁 3개를 작성하라.
2. 각 팁은 30자 내외의 한 문장이어야 한다.
3. 'section1', 'title' 같은 복잡한 구조는 절대 사용하지 마라.
4. 반드시 아래 JSON 형식으로만 응답하라:
{{"insights": ["팁1", "팁2", "팁3"]}}
"""

            # 4. OpenAI KEY 확인
            if not config.OPENAI_API_KEY:
                logger.warning("OPENAI_API_KEY not set, returning fallback insights")
                return {
                    "mission_rate": 0,
                    "insights": [
                        "",
                        "",
                        "",
                    ],
                }

            total_plans_task = PlanCheckList.filter(user=user).count()
            completed_plans_task = PlanCheckList.filter(user=user, is_completed=True).count()
            total_plans, completed_plans = await asyncio.gather(total_plans_task, completed_plans_task)
            mission_rate = int(completed_plans / total_plans * 100) if total_plans > 0 else 0

            # 4. OpenAI 호출 (데이터 페칭 후 한 번만 실행)
            client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 친절한 건강 생활 코치입니다. JSON 형식으로만 응답합니다, 다른 설명이나 섹션은 포함하지 마세요.",
                    },
                    {"role": "user", "content": context},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=200,
            )

            raw_content = response.choices[0].message.content or ""
            insights_data = json.loads(raw_content)
            tips = insights_data.get("insights", ["", "", ""])

            return {"result": tips, "mission_rate": mission_rate}

        except Exception as e:
            logger.error(f"Failed to generate insights: {e}")
            return {
                "insights": [
                    "",
                    "",
                    "",
                ],
                "mission_rate": 0,
            }

    async def generate_health_metric_summary(self, user: User) -> dict:
        """오늘 혈압/혈당 기록 요약 반환"""
        try:
            today_kst = datetime.now(KST).date()

            # 병렬 실행
            bp_task = BloodPressureRecord.filter(user=user).order_by("-created_at").limit(30)
            bs_task = BloodSugarRecord.filter(user=user).order_by("-created_at").limit(45)
            bp_records, bs_records = await asyncio.gather(bp_task, bs_task)

            def is_today_kst(dt):
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=ZoneInfo("UTC"))
                return dt.astimezone(KST).date() == today_kst

            today_bp = [r for r in bp_records if r.measure_type != "임의" and is_today_kst(r.created_at)]
            today_bs = [r for r in bs_records if r.measure_type != "임의" and is_today_kst(r.created_at)]

            def latest_by_type(records, measure_type):
                for r in records:
                    if r.measure_type == measure_type:
                        return r
                return None

            morning = latest_by_type(today_bp, "아침")
            evening = latest_by_type(today_bp, "저녁")

            fasting = latest_by_type(today_bs, "공복")
            postmeal = latest_by_type(today_bs, "식후 2시간")
            bedtime = latest_by_type(today_bs, "취침 전")

            return {
                "blood_pressure": {
                    "title": "오늘 혈압 기록",
                    "items": [
                        {
                            "label": "아침",
                            "value": f"{morning.systolic} / {morning.diastolic} mmHg" if morning else "미기록",
                            "status": "recorded" if morning else "pending",
                            "value_class": get_bp_value_class(morning.systolic, morning.diastolic)
                            if morning
                            else "pending",
                        },
                        {
                            "label": "저녁",
                            "value": f"{evening.systolic} / {evening.diastolic} mmHg" if evening else "미기록",
                            "status": "recorded" if evening else "pending",
                            "value_class": get_bp_value_class(evening.systolic, evening.diastolic)
                            if evening
                            else "pending",
                        },
                    ],
                },
                "blood_sugar": {
                    "title": "오늘 혈당 기록",
                    "items": [
                        {
                            "label": "공복",
                            "value": f"{int(fasting.glucose_mg_dl)} mg/dL" if fasting else "미기록",
                            "status": "recorded" if fasting else "pending",
                            "value_class": get_bs_value_class("공복", fasting.glucose_mg_dl) if fasting else "pending",
                        },
                        {
                            "label": "식후 2시간",
                            "value": f"{int(postmeal.glucose_mg_dl)} mg/dL" if postmeal else "미기록",
                            "status": "recorded" if postmeal else "pending",
                            "value_class": get_bs_value_class("식후 2시간", postmeal.glucose_mg_dl)
                            if postmeal
                            else "pending",
                        },
                        {
                            "label": "취침 전",
                            "value": f"{int(bedtime.glucose_mg_dl)} mg/dL" if bedtime else "미기록",
                            "status": "recorded" if bedtime else "pending",
                            "value_class": get_bs_value_class("취침 전", bedtime.glucose_mg_dl)
                            if bedtime
                            else "pending",
                        },
                    ],
                },
            }
        except Exception as e:
            logger.error(f"Failed to generate health metric summary: {e}")
            return {
                "blood_pressure": {
                    "title": "오늘 혈압 기록",
                    "items": [
                        {"label": "아침", "value": "미기록", "status": "pending", "value_class": "pending"},
                        {"label": "저녁", "value": "미기록", "status": "pending", "value_class": "pending"},
                    ],
                },
                "blood_sugar": {
                    "title": "오늘 혈당 기록",
                    "items": [
                        {"label": "공복", "value": "미기록", "status": "pending", "value_class": "pending"},
                        {"label": "식후 2시간", "value": "미기록", "status": "pending", "value_class": "pending"},
                        {"label": "취침 전", "value": "미기록", "status": "pending", "value_class": "pending"},
                    ],
                },
            }
