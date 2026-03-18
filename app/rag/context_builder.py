# 검색된 문서들을 LLM이 읽기 좋은 하나의 참고 문맥 문자열로 묶는 역할
# app/rag/context_builder.py

from typing import Any


def extract_unique_documents(results_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    여러 query의 검색 결과에서 문서를 모으고,
    중복 id를 제거해서 고유 문서 목록으로 반환한다.
    """
    unique_docs = {}

    for results in results_list:
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc_id, doc_text, metadata, distance in zip(ids, documents, metadatas, distances, strict=False):
            if doc_id not in unique_docs:
                unique_docs[doc_id] = {
                    "id": doc_id,
                    "text": doc_text,
                    "metadata": metadata,
                    "distance": distance,
                }

    return list(unique_docs.values())


def sort_documents_by_distance(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    distance 기준으로 문서를 정렬한다.
    공공기관 출처 문서를 우선하고, distance가 작을수록 더 유사한 문서다.
    """
    priority_sources = {"국가건강정보포털", "질병관리청"}

    def sort_key(x: dict[str, Any]) -> tuple[int, float]:
        source = x.get("metadata", {}).get("source", "")
        is_priority = 0 if source in priority_sources else 1
        return (is_priority, x.get("distance", 999999))

    return sorted(documents, key=sort_key)


def filter_documents_by_disease(
    documents: list[dict[str, Any]],
    selected_diseases: list[str],
) -> list[dict[str, Any]]:
    """
    선택된 질환과 관련된 문서만 우선 남긴다.
    - selected_diseases에 포함된 disease는 허용
    - disease가 '공통'인 문서는 허용
    - 그 외 다른 질환 문서는 제외
    """
    allowed_diseases = set(selected_diseases)
    allowed_diseases.add("공통")

    filtered = []
    for doc in documents:
        metadata = doc.get("metadata", {})
        disease = metadata.get("disease")
        if disease in allowed_diseases:
            filtered.append(doc)

    return filtered


def build_rag_context(
    documents: list[dict[str, Any]],
    max_docs: int = 5,
    include_metadata: bool = True,
) -> str:
    """
    검색된 문서 목록을 LLM prompt에 넣기 좋은 rag_context 문자열로 만든다.
    """
    if not documents:
        return "[참고 의료 정보]\n관련 참고 문서를 찾지 못했습니다."

    selected_docs = documents[:max_docs]

    lines = ["[참고 의료 정보]"]

    for idx, doc in enumerate(selected_docs, start=1):
        text = doc["text"].strip()

        if include_metadata:
            source = doc["metadata"].get("source", "알 수 없음")
            lines.append(f"{idx}. [출처: {source}] {text}")
        else:
            lines.append(f"{idx}. {text}")

    return "\n".join(lines)


def build_context_from_search_results(
    results_list: list[dict[str, Any]],
    selected_diseases: list[str] | None = None,
    max_docs: int = 5,
    include_metadata: bool = True,
) -> str:
    """
    여러 query 검색 결과를 받아
    중복 제거 -> 질환 필터링 -> 정렬 -> rag_context 생성까지 한 번에 처리한다.
    """
    unique_docs = extract_unique_documents(results_list)

    if selected_diseases:
        filtered_docs = filter_documents_by_disease(unique_docs, selected_diseases)
    else:
        filtered_docs = unique_docs

    sorted_docs = sort_documents_by_distance(filtered_docs)
    rag_context = build_rag_context(
        documents=sorted_docs,
        max_docs=max_docs,
        include_metadata=include_metadata,
    )
    return rag_context
