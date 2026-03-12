import json
from pathlib import Path

BASE_DIR = Path("app/rag/data")
INPUT_FILES = [
    BASE_DIR / "kdca_documents.jsonl",
    BASE_DIR / "common_lifestyle_documents.jsonl",
]
OUTPUT_FILE = BASE_DIR / "merged_documents.jsonl"


def load_jsonl(file_path: Path) -> list[dict]:
    documents: list[dict] = []

    if not file_path.exists():
        print(f"[WARN] File not found: {file_path}")
        return documents

    with file_path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                doc = json.loads(line)
                documents.append(doc)
            except json.JSONDecodeError as e:
                print(f"[ERROR] JSON parse failed: {file_path} line {line_num}")
                print(f"       {e}")

    return documents


def merge_jsonl_files(input_files: list[Path], output_file: Path) -> None:
    merged_docs: list[dict] = []
    seen_ids = set()

    for file_path in input_files:
        docs = load_jsonl(file_path)

        for doc in docs:
            doc_id = doc.get("id")

            if not doc_id:
                print(f"[WARN] Missing id in document from {file_path}")
                continue

            if doc_id in seen_ids:
                print(f"[WARN] Duplicate id skipped: {doc_id}")
                continue

            seen_ids.add(doc_id)
            merged_docs.append(doc)

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as f:
        for doc in merged_docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(f"[INFO] Merged {len(merged_docs)} documents into {output_file}")


if __name__ == "__main__":
    merge_jsonl_files(INPUT_FILES, OUTPUT_FILE)
