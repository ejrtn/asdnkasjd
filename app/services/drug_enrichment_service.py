import asyncio
import logging
from typing import Any, cast

from tortoise.expressions import F, Q

from app.dtos.drug_enrichment import DrugEnrichmentData
from app.models.drug_master_tmp import DrugMasterTmp
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class DrugEnrichmentService:
    """
    비어있는 의약품 정보를 LLM을 통해 보충하는 서비스입니다.
    """

    def __init__(self):
        self.llm_service = LLMService()

    async def enrich_incomplete_drugs(self, model: Any = DrugMasterTmp, page_size: int = 100) -> dict[str, Any]:
        """
        병렬 처리를 통해 LLM 보충 속도를 극대화합니다.
        """
        enriched_count = 0
        total_processed = 0

        # 동시에 실행할 최대 LLM 요청 수 (API Rate Limit에 따라 조절)
        # 예: 5개 배치(각 20개씩 총 100개)를 동시에 LLM에 요청
        semaphore = asyncio.Semaphore(5)

        async def process_batch(batch):
            nonlocal enriched_count
            async with semaphore:
                try:
                    batch_results = await self._generate_batch_drug_info(batch)
                    if not batch_results:
                        return

                    # DB 업데이트 로직 (업데이트는 순차적으로 해도 LLM 호출이 병렬이면 훨씬 빠름)
                    for drug in batch:
                        result = batch_results.get(drug.item_seq)
                        if result:
                            update_data = result if isinstance(result, dict) else result.model_dump()
                            update_data["source"] = "AI"
                            # update_from_dict 사용 후 저장
                            drug.update_from_dict(update_data)
                            # AI 보충 시점의 식약처 날짜 기록
                            drug.last_enriched_mfds_date = drug.mfds_update_date
                            await drug.save()
                            enriched_count += 1
                except Exception as e:
                    logger.error(f"Error processing batch: {e}")

        while True:
            # [수정] 정보가 없거나(null), 식약처 데이터가 우리 DB보다 최신인 경우만 가져옵니다.
            incomplete_drugs = (
                await model.filter(
                    Q(efcy_qesitm__isnull=True)  # 필수 정보가 없거나
                    | (
                        Q(mfds_update_date__isnull=False)  # 식약처 날짜 정보가 있는 경우 중
                        & (
                            Q(last_enriched_mfds_date__isnull=True)  # 아직 보충 전이거나
                            | Q(mfds_update_date__gt=F("last_enriched_mfds_date"))  # 보충 이후에 데이터가 갱신됨
                        )
                    )
                )
                .limit(page_size)
                .all()
            )

            if not incomplete_drugs:
                logger.info("No more incomplete drugs found.")
                break

            total_processed += len(incomplete_drugs)
            logger.info(f"Fetched {len(incomplete_drugs)} items. Total processed so far: {total_processed}")

            # 20개씩 소그룹 생성
            llm_batch_size = 20
            tasks = []
            for i in range(0, len(incomplete_drugs), llm_batch_size):
                sub_batch = incomplete_drugs[i : i + llm_batch_size]
                tasks.append(process_batch(sub_batch))

            # 동시에 실행 (병렬 호출)
            await asyncio.gather(*tasks)

            logger.info(f"Current Progress: Enriched {enriched_count} / Processed {total_processed}")

            # API 과부하 방지를 위한 미세 대기 (필요시)
            await asyncio.sleep(0.1)

        return {
            "status": "success",
            "enriched_count": enriched_count,
            "total_processed": total_processed,
        }

    async def _generate_batch_drug_info(self, drugs: list[Any]) -> dict[str, Any]:
        """
        여러 개의 약물 정보를 한 번의 LLM 호출로 생성합니다.
        """
        drug_details = []
        for d in drugs:
            drug_details.append(
                f"- ID: {d.item_seq}, 이름: {d.item_name}, 제조사: {d.entp_name}, 제형: {d.form_code_name}, 식별문구: {d.print_front}/{d.print_back}"
            )

        drugs_str = "\n".join(drug_details)

        prompt = f"""
당신은 베테랑 약사 AI입니다. 다음 리스트의 각 의약품에 대해 환자가 이해하기 쉬운 상세 정보를 생성해주세요.
부족한 정보는 전문 지식을 바탕으로 가장 일반적이고 안전한 정보를 채워주세요.

[의약품 리스트]
{drugs_str}

[출력 형식]
반드시 다음 JSON 구조로 응답해야 하며, 키값은 'ID'를 사용하세요. 모든 내용은 한국어로 작성합니다.

{{
  "ID_VALUE": {{
    "efcy_qesitm": "효능 요약 (한 줄)",
    "use_method_qesitm": "복용법 및 사용법",
    "atpn_warn_qesitm": "중요한 경고 (없으면 null)",
    "atpn_qesitm": "주의사항",
    "intrc_qesitm": "상호작용/금기 (없으면 null)",
    "se_qesitm": "주요 부작용 (없으면 null)",
    "deposit_method_qesitm": "보관법"
  }},
  ...
}}
"""
        messages = [
            {
                "role": "system",
                "content": "당신은 의약품 정보를 대량으로 분석하여 JSON 형식으로 설명하는 전문 약사 AI입니다.",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            # generate_json을 사용하여 응답을 딕셔너리로 직접 받음
            results = await self.llm_service.generate_json(messages)
            return cast(dict[str, Any], results)
        except Exception as e:
            logger.error(f"Batch LLM JSON generation failed: {e}")
            return {}

    async def _generate_drug_info(self, drug: Any) -> Any | None:
        """단일 약물 처리 (기존 호환성용)"""
        results = await self._generate_batch_drug_info([drug])
        if results and drug.item_seq in results:
            return DrugEnrichmentData(**results[drug.item_seq])
        return None
