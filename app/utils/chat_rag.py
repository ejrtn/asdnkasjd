from pathlib import Path


def load_rag_docs() -> list[dict[str, str]]:
    """
    app/data/docs/ 아래의 모든 .txt 파일을 로드
    """
    docs_dir = Path("app/data/docs")
    docs: list[dict[str, str]] = []

    if not docs_dir.exists():
        return docs

    for path in docs_dir.glob("*.txt"):
        try:
            text = path.read_text(encoding="utf-8")
            docs.append({"filename": path.name, "text": text})
        except Exception:
            continue

    return docs


def score_document(doc_text: str, doc_filename: str, keywords: list[str]) -> int:
    """문서와 키워드 매칭 점수 계산"""
    score = 0
    doc_filename_lower = doc_filename.lower()

    # 키워드 매핑
    mapping = {
        "고혈압": "hypertension",
        "당뇨병": "diabetes",
        "복용": "medication",
        "저염식": "low_salt",
        "운동": "exercise",
        "약": "medication",
        "처방": "prescription",
        "증상": "symptom",
        "통증": "pain",
    }

    for keyword in keywords:
        if not keyword:
            continue

        # 본문 매칭
        if keyword in doc_text:
            score += 1

        # 파일명 매칭 (가중치 높음)
        keyword_lower = keyword.lower()
        if keyword_lower in doc_filename_lower:
            score += 2

        # 매핑된 영어 키워드 매칭
        if keyword in mapping and mapping[keyword] in doc_filename_lower:
            score += 2

    return score


def select_relevant_docs_by_query(query: str, max_docs: int = 3) -> list[dict[str, str]]:
    """
    사용자 질문을 기반으로 관련 문서 선택
    """
    rag_docs = load_rag_docs()
    if not rag_docs:
        return []

    # 질문에서 키워드 추출
    keywords = extract_keywords_from_query(query)

    # 문서 점수 계산
    scored_docs = []
    for doc in rag_docs:
        score = score_document(doc["text"], doc["filename"], keywords)
        scored_docs.append((score, doc))

    # 점수순 정렬
    scored_docs.sort(key=lambda x: x[0], reverse=True)

    # 점수가 0보다 큰 문서만 선택, 없으면 상위 문서 반환
    selected_docs = [doc for score, doc in scored_docs if score > 0]

    if not selected_docs:
        selected_docs = [doc for _, doc in scored_docs]

    return selected_docs[:max_docs]


def extract_keywords_from_query(query: str) -> list[str]:
    """질문에서 키워드 추출"""
    keywords = []

    # 의료 관련 키워드
    medical_keywords = [
        "고혈압",
        "당뇨병",
        "약",
        "복용",
        "처방",
        "증상",
        "통증",
        "아픔",
        "혈압",
        "혈당",
        "운동",
        "식단",
        "저염식",
        "알레르기",
        "부작용",
    ]

    for keyword in medical_keywords:
        if keyword in query:
            keywords.append(keyword)

    # 질문에서 명사 추출 (간단한 방식)
    words = query.split()
    for word in words:
        if len(word) >= 2:
            keywords.append(word)

    return list(set(keywords))  # 중복 제거
