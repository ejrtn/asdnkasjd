import json
from pathlib import Path

BASE_DIR = Path("app/rag/data")
INPUT_FILES = [
    BASE_DIR / "kdca_documents.jsonl",
    BASE_DIR / "common_lifestyle_documents.jsonl",
]


def make_tags(doc: dict) -> list[str]:
    metadata = doc.get("metadata", {})
    text = doc.get("text", "")

    disease = metadata.get("disease", "")
    topic = metadata.get("topic", "")

    tags = set()

    if disease:
        tags.add(disease)
    if topic:
        tags.add(topic)

    keyword_map = {
        "식이": ["식사", "염분", "나트륨", "채소", "과일", "과식", "야식", "가공식품", "당분"],
        "운동": ["운동", "걷기", "유산소", "근력", "신체활동"],
        "수면": ["수면", "잠", "취침", "기상", "불면", "코골이"],
        "흡연": ["흡연", "금연", "담배", "간접흡연"],
        "음주": ["음주", "절주", "술", "알코올"],
        "체중": ["체중", "비만", "과체중", "감량", "허리둘레"],
        "복약": ["복약", "약", "약물", "흡입제", "항응고제"],
        "환경": ["먼지", "꽃가루", "미세먼지", "환기", "담배 연기"],
        "관리": ["정기검진", "혈압", "혈당", "콜레스테롤", "진료", "검사"],
        "생활습관": ["스트레스", "생활습관", "규칙적", "리듬", "휴식"],
        "예방": ["예방", "낙상", "감염", "위험"],
    }

    for _, keywords in keyword_map.items():
        for keyword in keywords:
            if keyword in text:
                tags.add(keyword)

    return sorted(tags)


def add_tags_to_file(file_path: Path) -> None:
    docs: list[dict] = []

    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            docs.append(json.loads(line))

    for doc in docs:
        metadata = doc.setdefault("metadata", {})
        metadata["tags"] = make_tags(doc)

    with file_path.open("w", encoding="utf-8") as f:
        for doc in docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(f"[INFO] tags 추가 완료: {file_path.name}")


def main():
    for file_path in INPUT_FILES:
        if file_path.exists():
            add_tags_to_file(file_path)
        else:
            print(f"[WARN] 파일 없음: {file_path}")


if __name__ == "__main__":
    main()
