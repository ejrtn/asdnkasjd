import logging
import xml.etree.ElementTree as ET  # noqa: N817
from typing import Any

from tortoise.models import Model
from tortoise.transactions import in_transaction

from app.core.config import config
from app.core.http_client import http_client
from app.models.drug_master import DrugMaster
from app.models.drug_master_tmp import DrugMasterTmp
from app.services.drug_enrichment_service import DrugEnrichmentService

logger = logging.getLogger(__name__)


class DrugService:
    """
    공공데이터포털(식약처) API와 연동하여 의약품 정보를 가져오고 동기화하는 서비스입니다.
    """

    async def sync_drugs(
        self, batch_size: int = 100, auto_enrich: bool = False, use_staging: bool = True
    ) -> dict[str, Any]:
        """
        두 API에서 데이터를 가져와 DrugMaster 또는 DrugMasterTmp 테이블에 통합 저장(Upsert)합니다.
        기본적으로 staging 테이블(DrugMasterTmp)에 저장합니다.
        """
        if not config.MFDS_API_SERVICE_KEY:
            logger.warning("MFDS_API_SERVICE_KEY is empty. Synchronization will fail.")

        model: type[Model] = DrugMasterTmp if use_staging else DrugMaster
        logger.info(
            f"Starting drug synchronization (model: {model.__name__}, batch_size: {batch_size}, auto_enrich: {auto_enrich})"
        )

        # 1. 낱알식별 정보 전체 동기화
        total_idnt_count = await self._sync_identification_info(model, batch_size, use_staging)

        # 2. e약은요 개요정보 전체 동기화
        total_easy_count = await self._sync_easy_drug_info(model, batch_size, use_staging)

        # 3. 자동 LLM 정보 보충 (요청 시)
        enriched_info = None
        if auto_enrich:
            enricher = DrugEnrichmentService()
            # 전체 데이터 보충 (모델 전달)
            enriched_info = await enricher.enrich_incomplete_drugs(model=model)
            logger.info(f"Auto-enrichment sync complete: {enriched_info.get('enriched_count', 0)} drugs enriched.")

        logger.info(f"Sync complete. IDNT: {total_idnt_count}, EASY: {total_easy_count}")
        return {
            "status": "success",
            "identification_count": total_idnt_count,
            "easy_drug_count": total_easy_count,
            "enrichment": enriched_info,
        }

    async def _sync_identification_info(self, model: type[Model], batch_size: int, use_staging: bool) -> int:
        """낱알식별 정보 동기화 루프"""
        total = 0
        page = 1
        while True:
            idnt_list = await self._fetch_identification_info(batch_size, page)
            if not idnt_list:
                break

            for item in idnt_list:
                item_seq = item.get("ITEM_SEQ") or item.get("item_seq") or item.get("itemSeq")
                if not item_seq:
                    continue

                defaults = self._map_idnt_to_model(item)
                defaults["source"] = "MFDS"

                if use_staging:
                    existing = await DrugMaster.get_or_none(item_seq=item_seq)
                    if existing and existing.last_enriched_mfds_date:
                        # 기존 AI 보충 정보 보존
                        defaults.update(
                            {
                                "efcy_qesitm": existing.efcy_qesitm,
                                "use_method_qesitm": existing.use_method_qesitm,
                                "atpn_warn_qesitm": existing.atpn_warn_qesitm,
                                "atpn_qesitm": existing.atpn_qesitm,
                                "intrc_qesitm": existing.intrc_qesitm,
                                "se_qesitm": existing.se_qesitm,
                                "deposit_method_qesitm": existing.deposit_method_qesitm,
                                "source": existing.source,
                                "last_enriched_mfds_date": existing.last_enriched_mfds_date,
                            }
                        )

                await model.update_or_create(item_seq=item_seq, defaults=defaults)
                total += 1

            logger.info(f"Synced identification info page {page}: {len(idnt_list)} items")
            if len(idnt_list) < batch_size:
                break
            page += 1
        return total

    async def _sync_easy_drug_info(self, model: type[Model], batch_size: int, use_staging: bool) -> int:
        """e약은요 정보 동기화 루프"""
        total = 0
        page = 1
        while True:
            easy_list = await self._fetch_easy_drug_info(batch_size, page)
            if not easy_list:
                break

            for item in easy_list:
                item_seq = item.get("itemSeq")
                if not item_seq:
                    continue

                defaults = self._map_easy_to_model(item)
                defaults["source"] = "MFDS"

                if use_staging:
                    existing = await DrugMaster.get_or_none(item_seq=item_seq)
                    if existing and existing.last_enriched_mfds_date:
                        # 기존 AI 보충 정보 보존 (e약은요가 제공하지 않는 필드들 위주로)
                        # e약은요에서 가져온 값(defaults)이 비어있을 때만 기존 AI 정보를 사용하거나
                        # 혹은 AI 정보가 더 풍부하다면 덮어쓰지 않도록 설계
                        for field in [
                            "efcy_qesitm",
                            "use_method_qesitm",
                            "atpn_warn_qesitm",
                            "atpn_qesitm",
                            "intrc_qesitm",
                            "se_qesitm",
                            "deposit_method_qesitm",
                        ]:
                            if not defaults.get(field) and getattr(existing, field):
                                defaults[field] = getattr(existing, field)

                        defaults["source"] = existing.source
                        defaults["last_enriched_mfds_date"] = existing.last_enriched_mfds_date

                await model.update_or_create(item_seq=item_seq, defaults=defaults)
                total += 1

            logger.info(f"Synced easy drug info page {page}: {len(easy_list)} items")
            if len(easy_list) < batch_size:
                break
            page += 1
        return total

    async def promote_tmp_to_production(self) -> dict[str, Any]:
        """
        임시 테이블(DrugMasterTmp)의 데이터를 메인 테이블(DrugMaster)로 이전합니다.
        """

        logger.info("Promoting Staging data to Production...")

        try:
            async with in_transaction():
                # 1. 메인 테이블 비우기
                await DrugMaster.all().delete()

                # 2. 임시 테이블 데이터를 메인 테이블로 전체 복사
                all_tmp = await DrugMasterTmp.all()
                production_batch = []
                for tmp in all_tmp:
                    data = {}
                    for field in tmp._meta.fields_map.keys():
                        if field in ["created_at", "updated_at"]:
                            continue
                        data[field] = getattr(tmp, field)

                    production_batch.append(DrugMaster(**data))

                # 500개씩 벌크 생성
                for i in range(0, len(production_batch), 500):
                    await DrugMaster.bulk_create(production_batch[i : i + 500])

                logger.info(f"Successfully promoted {len(production_batch)} items to Production.")

                # 3. 임시 테이블 비우기
                await DrugMasterTmp.all().delete()

            return {"status": "success", "promoted_count": len(production_batch)}
        except Exception as e:
            logger.error(f"Failed to promote drug data: {e}")
            return {"status": "error", "message": str(e)}

    async def _fetch_identification_info(self, batch_size: int, page_no: int) -> list[dict[str, Any]]:
        """낱알식별 정보 API 호출 및 파싱"""
        params: dict[str, str | int | None] = {
            "serviceKey": config.MFDS_API_SERVICE_KEY,
            "numOfRows": batch_size,
            "pageNo": page_no,
        }
        try:
            response = await http_client.client.get(config.MFDS_IDNT03_API_URL, params=params)
            response.raise_for_status()
            return self._parse_xml_to_dict(response.text, "item")
        except Exception as e:
            logger.error(f"Error fetching identification info (page {page_no}): {e}")
            return []

    async def _fetch_easy_drug_info(self, batch_size: int, page_no: int) -> list[dict[str, Any]]:
        """e약은요 개요정보 API 호출 및 파싱"""
        params: dict[str, str | int | None] = {
            "serviceKey": config.MFDS_API_SERVICE_KEY,
            "numOfRows": batch_size,
            "pageNo": page_no,
        }
        try:
            response = await http_client.client.get(config.MFDS_E_DRUG_API_URL, params=params)
            response.raise_for_status()
            return self._parse_xml_to_dict(response.text, "item")
        except Exception as e:
            logger.error(f"Error fetching easy drug info (page {page_no}): {e}")
            return []

    def _parse_xml_to_dict(self, xml_content: str, item_tag: str) -> list[dict[str, Any]]:
        """XML 응답을 딕셔너리 리스트로 변환"""
        try:
            root = ET.fromstring(xml_content)
            items = []
            for item in root.findall(f".//{item_tag}"):
                item_dict = {}
                for child in item:
                    item_dict[child.tag] = child.text
                items.append(item_dict)
            return items
        except Exception as e:
            logger.error(f"XML parsing error: {e}")
            return []

    def _map_idnt_to_model(self, item: dict[str, Any]) -> dict[str, Any]:
        """낱알식별 데이터를 모델 필드에 맞게 매핑"""
        return {
            "item_name": item.get("ITEM_NAME") or item.get("item_name") or item.get("itemName"),
            "entp_name": item.get("ENTP_NAME") or item.get("entp_name") or item.get("entpName"),
            "chart": item.get("CHART") or item.get("chart"),
            "item_image": item.get("ITEM_IMAGE") or item.get("item_image") or item.get("itemImage"),
            "print_front": item.get("PRINT_FRONT") or item.get("print_front"),
            "print_back": item.get("PRINT_BACK") or item.get("print_back"),
            "drug_shape": item.get("DRUG_SHAPE") or item.get("drug_shape"),
            "color_class1": item.get("COLOR_CLASS1") or item.get("color_class1"),
            "color_class2": item.get("COLOR_CLASS2") or item.get("color_class2"),
            "line_front": item.get("LINE_FRONT") or item.get("line_front"),
            "line_back": item.get("LINE_BACK") or item.get("line_back"),
            "form_code_name": item.get("FORM_CODE_NAME") or item.get("form_code_name"),
            "etc_otc_name": item.get("ETC_OTC_NAME") or item.get("etc_otc_name"),
            "class_name": item.get("CLASS_NAME") or item.get("class_name"),
            "mfds_update_date": (
                (
                    item.get("CHANGE_DATE")
                    or item.get("change_date")
                    or item.get("LAST_UPDT_DTM")
                    or item.get("last_updt_dtm")
                    or ""
                ).replace("-", "")
                or None
            ),
        }

    def _map_easy_to_model(self, item: dict[str, Any]) -> dict[str, Any]:
        """e약은요 데이터를 모델 필드에 맞게 매핑"""
        return {
            "item_name": item.get("itemName"),
            "entp_name": item.get("entpName"),
            "efcy_qesitm": item.get("efcyQesitm"),
            "use_method_qesitm": item.get("useMethodQesitm"),
            "atpn_warn_qesitm": item.get("atpnWarnQesitm"),
            "atpn_qesitm": item.get("atpnQesitm"),
            "intrc_qesitm": item.get("intrcQesitm"),
            "se_qesitm": item.get("seQesitm"),
            "deposit_method_qesitm": item.get("depositMethodQesitm"),
            "item_image": item.get("itemImage") or item.get("ITEM_IMAGE"),
            "mfds_update_date": (
                (item.get("updateDe") or item.get("UPDATE_DE") or item.get("LAST_UPDT_DTM") or "").replace("-", "")
                or None
            ),
        }
