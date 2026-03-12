from typing import Any

from app.rag.taxonomy import (
    LIFESTYLE_TOPIC_RULES,
    find_disease_group,
    is_known_disease,
)


def normalize_user_diseases(selected_diseases: list[str], other_disease: str | None = None) -> list[dict[str, str]]:
    normalized = []

    for disease in selected_diseases:
        normalized.append({"name": disease, "group": find_disease_group(disease)})

    if other_disease:
        other_disease = other_disease.strip()
        if other_disease:
            if is_known_disease(other_disease):
                normalized.append({"name": other_disease, "group": find_disease_group(other_disease)})
            else:
                normalized.append({"name": other_disease, "group": "기타"})

    return normalized


def extract_topics_from_lifestyle(lifestyle: dict[str, Any]) -> list[str]:
    topics = set()

    for field_name, value_topic_map in LIFESTYLE_TOPIC_RULES.items():
        user_value = lifestyle.get(field_name)
        if user_value in value_topic_map:
            for topic in value_topic_map[user_value]:
                topics.add(topic)

    return list(topics)


def build_queries(
    diseases: list[dict[str, str]],
    lifestyle: dict[str, Any],
    include_default_topics: bool = True,
) -> list[str]:
    queries = set()

    # JSONL metadata topic과 최대한 맞추기
    default_topics = ["식이", "운동", "복약", "관리", "예방", "생활습관"] if include_default_topics else []
    lifestyle_topics = extract_topics_from_lifestyle(lifestyle)

    # topic 이름 통일
    topic_alias_map = {
        "금연": "흡연",
        "절주": "음주",
        "모니터링": "관리",
        "합병증예방": "예방",
    }

    normalized_lifestyle_topics = []
    for topic in lifestyle_topics:
        normalized_lifestyle_topics.append(topic_alias_map.get(topic, topic))

    final_topics = set(default_topics + normalized_lifestyle_topics)

    for disease in diseases:
        disease_name = disease["name"]

        # 넓은 query
        queries.add(f"{disease_name} 생활습관")
        queries.add(f"{disease_name} 관리")

        for topic in final_topics:
            queries.add(f"{disease_name} {topic}")
            queries.add(f"{disease_name} {topic} 관리")

    return sorted(list(queries))
