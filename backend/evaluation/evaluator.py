import json
from pathlib import Path

from documents.services.retriever import Retriever
from evaluation.metrics import retrieval_hit


def load_test_cases():

    dataset = Path(__file__).resolve().parent / "datasets" / "rag_test_cases.json"
    return json.loads(dataset.read_text(encoding="utf-8"))


def evaluate_retrieval(document_id):

    test_cases = load_test_cases()

    results = []

    for test_case in test_cases:

        chunks = Retriever.retrieve(
            query=test_case["question"],
            document_id=document_id,
            top_k=5
        )

        rank = retrieval_hit(chunks, test_case["evidence_snippet"])

        results.append({
            "id": test_case["id"],
            "question": test_case["question"],
            "reciprocal_rank": rank
        })

    return results
