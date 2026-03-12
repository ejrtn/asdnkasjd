# profile_mapper.py: DB 객체를 RAG 입력값으로 바꾸기
# rag_pipeline.py: query 생성, 검색, context 만들기
# 사용자 건강정보 → RAG 검색 → rag_context 생성
# app/rag/rag_pipeline.py

from app.rag.context_builder import build_context_from_search_results
from app.rag.query_builder import build_queries, normalize_user_diseases
from app.rag.vector_store import search_similar_documents


def generate_rag_context(
    selected_diseases: list[str],
    other_disease: str | None,
    lifestyle: dict,
    max_queries: int = 5,
    top_k: int = 3,
) -> str:
    """
    사용자 건강정보 기반 RAG context 생성
    """

    # 1️⃣ 질환 정규화
    diseases = normalize_user_diseases(selected_diseases, other_disease)

    # 2️⃣ query 생성
    queries = build_queries(diseases, lifestyle)

    # 3️⃣ vector search
    results_list = []
    for query in queries[:max_queries]:
        results = search_similar_documents(
            query_text=query,
            n_results=top_k,
        )
        results_list.append(results)

    # 4️⃣ rag_context 생성
    rag_context = build_context_from_search_results(
        results_list=results_list,
        selected_diseases=selected_diseases,
        max_docs=5,
        include_metadata=True,
    )

    return rag_context
