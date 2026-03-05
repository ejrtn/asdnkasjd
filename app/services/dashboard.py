import json
import logging

from openai import AsyncOpenAI

from app.core import config
from app.models.blood_pressure_record import BloodPressureRecord
from app.models.blood_sugar_record import BloodSugarRecord
from app.models.health_profile import HealthProfile
from app.models.user import User

logger = logging.getLogger(__name__)


class DashboardService:
    async def generate_insights(self, user: User) -> dict:
        """사용자 건강 정보 기반 AI 인사이트 3개 생성"""
        try:
            # 1. 사용자 건강 데이터 수집
            health_profile = await HealthProfile.get_or_none(user=user)
            bp_records = await BloodPressureRecord.filter(user=user).order_by("-created_at").limit(7)
            bs_records = await BloodSugarRecord.filter(user=user).order_by("-created_at").limit(7)

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
- 신장: {health_profile.height_cm if health_profile else "N/A"}cm
- 체중: {health_profile.weight_kg if health_profile else "N/A"}kg
- 흡연: {health_profile.smoking_status if health_profile else "N/A"}
- 음주: {health_profile.drinking_status if health_profile else "N/A"}
- 운동: {health_profile.exercise_frequency if health_profile else "N/A"}
- 식습관: {health_profile.diet_type if health_profile else "N/A"}
- 최근 7일 평균 혈압: {bp_avg or "N/A"}
- 최근 7일 평균 혈당: {f"{bs_avg:.0f}" if bs_avg else "N/A"} mg/dL

위 정보를 바탕으로 사용자에게 도움이 될 만한 건강 생활 팁 3개를 한 문장씩 작성해주세요.
각 문장은 50자 이내여야 하고, 긍정적이고 실행 가능한 조언이어야 합니다.
반드시 아래 JSON 형식으로만 응답하세요:
{{"insights": ["팁1", "팁2", "팁3"]}}
"""

            # 4. OpenAI 호출
            if not config.OPENAI_API_KEY:
                logger.warning("OPENAI_API_KEY not set, returning fallback insights")
                return {
                    "score": 82,
                    "insights": [
                        "물 한 잔으로 오늘을 가볍게 시작해요.",
                        "스트레칭 3분이면 몸이 훨씬 편해져요.",
                        "잠들기 30분 전 깊은 호흡은 숙면에 도움돼요.",
                    ],
                }

            client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 친절한 건강 생활 코치입니다. JSON 형식으로만 응답합니다.",
                    },
                    {"role": "user", "content": context},
                ],
                temperature=0.7,
                max_tokens=200,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            insights = data.get("insights", [])[:3]

            return {"score": 82, "insights": insights}

        except Exception as e:
            logger.error(f"Failed to generate insights: {e}")
            return {
                "score": 82,
                "insights": [
                    "물 한 잔으로 오늘을 가볍게 시작해요.",
                    "스트레칭 3분이면 몸이 훨씬 편해져요.",
                    "잠들기 30분 전 화면을 줄이면 숙면에 도움돼요.",
                ],
            }
