import os
from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/current")
async def get_current_weather(lat: float | None = None, lon: float | None = None, city: str = "Seoul"):
    """현재 날씨 정보를 가져옵니다."""

    weather_api_key = os.getenv("WEATHER_API_KEY")
    if not weather_api_key:
        raise HTTPException(
            status_code=500, detail="WEATHER_API_KEY is not set. Put it in .env or environment variables."
        )

    base_url = "https://api.openweathermap.org/data/2.5/weather"

    if lat is not None and lon is not None:
        params: dict[str, str | float] = {
            "lat": lat,
            "lon": lon,
            "appid": weather_api_key,
            "units": "metric",
            "lang": "kr",
        }
    else:
        params = {"q": city, "appid": weather_api_key, "units": "metric", "lang": "kr"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

        weather_icons = {
            "01d": "☀️",
            "01n": "🌙",
            "02d": "⛅",
            "02n": "☁️",
            "03d": "☁️",
            "03n": "☁️",
            "04d": "☁️",
            "04n": "☁️",
            "09d": "🌧️",
            "09n": "🌧️",
            "10d": "🌦️",
            "10n": "🌧️",
            "11d": "⛈️",
            "11n": "⛈️",
            "13d": "❄️",
            "13n": "❄️",
            "50d": "🌫️",
            "50n": "🌫️",
        }

        # icon_code 기준 감성적 한줄 매핑
        tips = {
            "01d": "햇빛 좋은 날이에요. 가벼운 산책 10분만 해도 충분해요.",
            "01n": "오늘은 밤 공기가 맑아요. 잠들기 전 가벼운 스트레칭 어때요?",
            "02d": "구름 사이로 햇빛이 비쳐요. 야외활동하기 좋은 날씨입니다.",
            "02n": "흐린 밤이네요. 편안한 저녁 시간을 보내세요.",
            "03d": "흐린 날씨네요. 실내에서 가벼운 스트레칭을 해보세요.",
            "03n": "흐린 밤이에요. 실내에서 편히 쉬어보세요.",
            "04d": "흐린 날씨네요. 실내에서 가벼운 스트레칭을 해보세요.",
            "04n": "흐린 밤이에요. 실내에서 편히 쉬어보세요.",
            "09d": "비 오는 날엔 실내 스트레칭으로 몸을 풀어볼까요?",
            "09n": "밤에 비가 오네요. 따뜻한 실내에서 휴식을 취하세요.",
            "10d": "비가 오면 몸이 처질 수 있어요. 따뜻한 물 한 잔부터 시작해요.",
            "10n": "밤에 비가 오네요. 따뜻한 실내에서 휴식을 취하세요.",
            "11d": "천둥번개가 칠 수 있으니 안전한 실내에 머물러요.",
            "11n": "천둥번개가 칠 수 있으니 안전한 실내에 머물러요.",
            "13d": "추운 날엔 혈압이 오를 수 있어요. 따뜻하게 챙겨 입어요.",
            "13n": "추운 밤이에요. 따뜻하게 챙겨 입고 푹 쉬어요.",
            "50d": "안개 낀 날엔 호흡이 답답할 수 있어요. 무리한 야외활동은 피하세요.",
            "50n": "안개 낀 밤이에요. 실내에서 편히 쉬어보세요.",
        }

        now = datetime.now()
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        date_text = f"📅 {now.year}년 {now.month}월 {now.day}일 {weekdays[now.weekday()]}"

        temp = round(data["main"]["temp"])
        weather_desc = data["weather"][0]["description"]
        weather_icon_code = data["weather"][0]["icon"]
        weather_icon = weather_icons.get(weather_icon_code, "🌤️")
        city_name = data["name"]

        tip = tips.get(weather_icon_code, "오늘도 몸이 편안해지는 작은 루틴 하나만 해봐요.")

        return {
            "date_text": date_text,
            "weather_text": f"{weather_icon} {temp}°C · {weather_desc}",
            "icon": weather_icon,
            "city": city_name,
            "temperature": temp,
            "description": weather_desc,
            "tip": tip,
        }

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502, detail=f"OpenWeather error: {e.response.status_code} / {e.response.text}"
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"날씨 정보를 가져올 수 없습니다: {str(e)}") from e
