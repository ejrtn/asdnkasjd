import logging
from typing import Any

from app.core.config import config
from app.core.http_client import http_client
from app.dtos.ocr import PillCandidate

logger = logging.getLogger(__name__)


class MFDSService:
    """
    공공데이터포털(data.go.kr)의 식품의약품안정처 낱알식별정보 API를 연동하는 서비스입니다.
    """

    def __init__(self):
        self.api_url = config.MFDS_API_URL
        self.service_key = config.MFDS_API_SERVICE_KEY

    async def search_pills(
        self,
        marking_front: str | None = None,
        marking_back: str | None = None,
        color: str | None = None,
        shape: str | None = None,
        name: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        MFDS API를 호출하여 검색 결과 리스트를 반환합니다.
        """
        if not self.service_key:
            logger.warning("MFDS_API_SERVICE_KEY가 설정되지 않았습니다.")
            return []

        params = {"serviceKey": self.service_key, "type": "json", "numOfRows": 20, "pageNo": 1}

        if marking_front:
            params["print_front"] = marking_front
        if marking_back:
            params["print_back"] = marking_back
        if color:
            params["color_class1"] = color
        if shape:
            params["drug_shape"] = shape
        if name:
            params["item_name"] = name

        try:
            client = http_client.client
            response = await client.get(self.api_url, params=params, timeout=10.0)

            if response.status_code != 200:
                logger.error(f"MFDS API Error: {response.status_code} - {response.text}")
                return []

            data = response.json()
            items = data.get("body", {}).get("items", [])
            if not items:
                return []

            return items if isinstance(items, list) else [items]
        except Exception as e:
            logger.error(f"MFDS API 요청 실패: {str(e)}")
            return []

    def calculate_similarity(self, analyzed: dict[str, Any], candidate: dict[str, Any]) -> float:
        """
        분석된 특성과 API 결과 후보의 유사도를 계산합니다 (0.0 ~ 1.0).
        """
        score = 0.0
        weights = {"marking": 0.5, "name": 0.2, "color": 0.15, "shape": 0.15}

        # 1. 각인 매칭 (가장 중요)
        target_front = str(candidate.get("PRINT_FRONT", "")).strip().upper()
        target_back = str(candidate.get("PRINT_BACK", "")).strip().upper()
        analyzed_front = str(analyzed.get("marking_front", "") or "").strip().upper()
        analyzed_back = str(analyzed.get("marking_back", "") or "").strip().upper()

        if analyzed_front == target_front:
            score += weights["marking"] * 0.6
        if analyzed_back == target_back:
            score += weights["marking"] * 0.4

        # 2. 이름 매칭 (있을 경우)
        if analyzed.get("name") and analyzed["name"] in candidate.get("ITEM_NAME", ""):
            score += weights["name"]

        # 3. 색상 매칭
        if analyzed.get("color") and analyzed["color"] in candidate.get("COLOR_NAME1", ""):
            score += weights["color"]

        # 4. 모양 매칭
        if analyzed.get("shape") and analyzed["shape"] in candidate.get("DRUG_SHAPE", ""):
            score += weights["shape"]

        return round(min(score, 1.0), 2)

    async def get_identified_candidates(self, analyzed_traits: dict[str, Any]) -> list[PillCandidate]:
        """
        분석된 특성을 기반으로 API 검색을 수행하고 유사도 순으로 정렬된 후보군을 반환합니다.
        여러 단계의 검색을 시도하여 검색 성공률을 높입니다.
        """
        search_strategies = self._build_search_strategies(analyzed_traits)
        all_items = await self._fetch_all_items(search_strategies)
        candidates = self._create_pill_candidates(analyzed_traits, all_items)

        # 유사도 순 정렬
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        return candidates[:4]  # 상위 4개 반환

    def _build_search_strategies(self, traits: dict[str, Any]) -> list[dict[str, str]]:
        """검색 시도 순서 전략을 생성합니다."""
        front = str(traits.get("marking_front", "") or "").replace(" ", "").upper()
        back = str(traits.get("marking_back", "") or "").replace(" ", "").upper()
        name = traits.get("name", "")
        color = traits.get("color")
        shape = traits.get("shape")

        strategies: list[dict[str, str]] = []
        if front and back:
            strategies.append({"marking_front": front, "marking_back": back})
        if front:
            strategies.append({"marking_front": front})
        if back:
            strategies.append({"marking_back": back})
        if name and len(name) > 1:
            strategies.append({"name": name})

        if color or shape:
            strategy: dict[str, str] = {}
            if color:
                strategy["color"] = str(color)
            if shape:
                strategy["shape"] = str(shape)
            strategies.append(strategy)
        return strategies

    async def _fetch_all_items(self, search_strategies: list[dict[str, str]]) -> list[dict[str, Any]]:
        """상세 검색 전략에 따라 API 아이템을 중복 없이 가져옵니다."""
        all_items = []
        seen_item_seqs = set()
        for strategy in search_strategies:
            logger.info(f"[MFDS API] Trying strategy: {strategy}")
            items = await self.search_pills(**strategy)
            for item in items:
                item_seq = item.get("ITEM_SEQ")
                if item_seq and item_seq not in seen_item_seqs:
                    all_items.append(item)
                    seen_item_seqs.add(item_seq)
            if len(all_items) >= 4:
                break
        return all_items

    def _create_pill_candidates(self, traits: dict[str, Any], items: list[dict[str, Any]]) -> list[PillCandidate]:
        """API 결과 아이템들을 PillCandidate DTO로 변환합니다."""
        candidates = []
        for item in items:
            similarity = self.calculate_similarity(traits, item)
            candidates.append(
                PillCandidate(
                    pill_name=item.get("ITEM_NAME", "알 수 없는 약품"),
                    confidence=similarity,
                    medication_info=item.get("CHART", "정보 없음"),
                    image_url=item.get("ITEM_IMAGE"),
                    item_seq=item.get("ITEM_SEQ"),
                    color=item.get("COLOR_NAME1"),
                    shape=item.get("DRUG_SHAPE"),
                    marking_front=item.get("PRINT_FRONT"),
                    marking_back=item.get("PRINT_BACK"),
                )
            )
        return candidates
