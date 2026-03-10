from pathlib import Path


class RagService:
    def load_rag_docs(self) -> list[dict[str, str]]:
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

    def score_document(self, doc_text: str, doc_filename: str, keywords: list[str]) -> int:
        score = 0
        doc_filename_lower = doc_filename.lower()

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

            if keyword in doc_text:
                score += 1

            keyword_lower = keyword.lower()
            if keyword_lower in doc_filename_lower:
                score += 2

            if keyword in mapping and mapping[keyword] in doc_filename_lower:
                score += 2

        return score

    def select_relevant_docs_by_keywords(
        self,
        keywords: list[str],
        max_docs: int = 3,
    ) -> list[dict[str, str]]:
        rag_docs = self.load_rag_docs()
        if not rag_docs:
            return []

        scored_docs = []
        for doc in rag_docs:
            score = self.score_document(doc["text"], doc["filename"], keywords)
            scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)
        selected_docs = [doc for score, doc in scored_docs if score > 0]

        if not selected_docs:
            selected_docs = [doc for _, doc in scored_docs]

        return selected_docs[:max_docs]

    def build_rag_context(self, docs: list[dict[str, str]]) -> str:
        if not docs:
            return "참고 문서 없음"
        return "\n\n".join(doc["text"] for doc in docs)

    def build_health_keywords(
        self,
        disease_list: list[str],
        med_list: list[str],
    ) -> list[str]:
        keywords = []
        keywords.extend(disease_list)
        keywords.extend(med_list)
        keywords.extend(["운동", "복용", "저염식", "혈압", "혈당"])
        return keywords

    def extract_keywords_from_query(self, query: str) -> list[str]:
        medical_keywords = [
            "고혈압",
            "당뇨병",
            "약",
            "복용",
            "복약",
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

        keywords = [kw for kw in medical_keywords if kw in query]

        words = query.split()
        for word in words:
            if len(word) >= 2 and word not in keywords:
                keywords.append(word)

        return keywords
