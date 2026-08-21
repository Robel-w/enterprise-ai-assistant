import json

from documents.services.retriever import Retriever
from evaluation.metrics import retrieval_hit


def load_test_cases():

    with open(
        "evaluation/datasets/rag_test_cases.json",
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def evaluate_retrieval(document_id):

    test_cases = load_test_cases()

    results = []

    for test_case in test_cases:

        chunks = Retriever.retrieve(
            query=test_case["question"],
            document_id=document_id,
            top_k=5
        )

        hit = retrieval_hit(
            chunks,
            test_case["expected_pages"]
        )

        results.append({
            "id": test_case["id"],
            "question": test_case["question"],
            "retrieval_hit": hit
        })

    return results