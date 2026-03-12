# app/rag/vector_store.py

import json
from pathlib import Path
from typing import Any

import chromadb

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = BASE_DIR / "chroma_db"

COLLECTION_NAME = "health_guidelines"


def load_jsonl_documents(file_path: str | Path) -> list[dict[str, Any]]:
    """
    JSONL 파일을 읽어서 문서 리스트로 반환한다.
    """
    file_path = Path(file_path)
    documents = []

    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            documents.append(json.loads(line))

    return documents


def get_chroma_client() -> Any:
    """
    로컬에 저장되는 Chroma PersistentClient를 생성한다.
    """
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def get_or_create_collection() -> Any:
    """
    health_guidelines collection을 가져오거나 새로 만든다.
    """
    client = get_chroma_client()
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return collection


def reset_collection() -> None:
    """
    기존 collection을 삭제 후 다시 생성한다.
    테스트할 때 중복 적재를 방지하기 위해 사용한다.
    """
    client = get_chroma_client()

    try:
        client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass

    client.get_or_create_collection(name=COLLECTION_NAME)


def build_sample_vector_store() -> None:
    """
    merged_documents.jsonl을 읽어서 Chroma collection에 저장한다.
    """
    file_path = DATA_DIR / "merged_documents.jsonl"
    docs = load_jsonl_documents(file_path)

    reset_collection()
    collection = get_or_create_collection()

    ids = []
    documents = []
    metadatas = []

    for doc in docs:
        ids.append(doc["id"])
        documents.append(doc["text"])
        metadatas.append(doc["metadata"])

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    print(f"총 {len(ids)}개의 문서를 collection에 저장했습니다.")


def search_similar_documents(query_text: str, n_results: int = 3) -> Any:
    """
    query_text로 유사 문서를 검색한다.
    """
    collection = get_or_create_collection()

    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
    )
    return results


def pretty_print_results(results: dict[str, Any]) -> None:
    """
    검색 결과를 보기 좋게 출력한다.
    """
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    ids = results.get("ids", [[]])[0]
    distances = results.get("distances", [[]])[0]

    print("\n검색 결과:")
    for idx, (doc_id, doc_text, metadata, distance) in enumerate(
        zip(ids, documents, metadatas, distances, strict=False), start=1
    ):
        print(f"\n[{idx}] id: {doc_id}")
        print(f"topic: {metadata.get('topic')}")
        print(f"disease: {metadata.get('disease')}")
        print(f"source: {metadata.get('source')}")
        print(f"distance: {distance}")
        print(f"text: {doc_text}")
