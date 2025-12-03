import csv
import os
import sys
from pathlib import Path
from typing import List, Dict

from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()

MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI environment variable is not set. Define it in .env before running the import script.")

DB_NAME = os.environ.get("MONGO_DB_NAME", "cybertest_db")
COLLECTION_NAME = os.environ.get("MONGO_QUESTIONS_COLLECTION", "questions")
ACTIVE_VERSION = os.environ.get("ACTIVE_VERSION", "12")

# CSV columns expected
REQUIRED_COLUMNS = {"question", "option1", "option2", "correct"}
OPTION_COLUMNS = ["option1", "option2", "option3", "option4"]

def load_csv(file_path: Path) -> List[Dict[str, str]]:
    with file_path.open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")
        rows = [row for row in reader if any(row.values())]
    if not rows:
        raise ValueError("CSV file appears to be empty.")
    return rows

def normalize_row(row: Dict[str, str]) -> Dict:
    question = (row.get("question") or "").strip()
    if len(question) < 10:
        raise ValueError(f"Question text too short: {question!r}")

    options = []
    for col in OPTION_COLUMNS:
        value = (row.get(col) or "").strip()
        if value:
            options.append(value)
    if len(options) < 2:
        raise ValueError(f"Question must have at least two options: {question}")

    correct = (row.get("correct") or "").strip()
    if correct not in options:
        raise ValueError(f"Correct answer '{correct}' not found in options for question: {question}")

    topic = (row.get("topic") or "").strip()

    return {
        "_id": str(ObjectId()),
        "version": ACTIVE_VERSION,
        "question": question,
        "options": options,
        "correct": correct,
        "topic": topic
    }


def import_questions(file_path: Path, replace_existing: bool = False) -> int:
    rows = load_csv(file_path)
    docs = [normalize_row(row) for row in rows]

    client = MongoClient(MONGO_URI)
    collection = client[DB_NAME][COLLECTION_NAME]

    if replace_existing:
        collection.delete_many({"version": ACTIVE_VERSION})

    # Avoid duplicates by checking existing question text within active version
    existing_texts = {
        doc["question"]
        for doc in collection.find({"version": ACTIVE_VERSION}, {"question": 1, "_id": 0})
    }

    new_docs = [doc for doc in docs if doc["question"] not in existing_texts]
    if not new_docs:
        print("No new questions to insert.")
        return 0

    collection.insert_many(new_docs)
    return len(new_docs)


def main(argv: List[str]) -> None:
    if len(argv) < 2:
        print("Usage: python import_questions.py <path/to/questions.csv> [--replace]")
        sys.exit(1)

    csv_path = Path(argv[1])
    if not csv_path.exists():
        print(f"File not found: {csv_path}")
        sys.exit(1)

    replace = "--replace" in argv[2:]
    try:
        inserted = import_questions(csv_path, replace_existing=replace)
    except Exception as exc:
        print(f"Error importing questions: {exc}")
        sys.exit(1)

    print(f"✅ Imported {inserted} question(s) for version {ACTIVE_VERSION} from {csv_path.name}")
    if replace:
        print("Existing questions for this version were replaced.")

if __name__ == "__main__":
    main(sys.argv)
