import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from documents.services.reranker import Reranker
from documents.services.retriever import Retriever
from evaluation.metrics import reciprocal_rank


class Command(BaseCommand):
    help = "Evaluate retrieval and reranking using evidence snippets in the committed dataset."

    def add_arguments(self, parser):
        parser.add_argument("--document-id", type=int, required=True)
        parser.add_argument("--dataset", type=Path)
        parser.add_argument("--retrieval-pool", type=int, default=20)
        parser.add_argument("--k", type=int, default=5)

    def handle(self, *args, **options):
        dataset_path = options["dataset"] or (
            settings.BASE_DIR / "evaluation" / "datasets" / "rag_test_cases.json"
        )
        try:
            cases = json.loads(dataset_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Could not load evaluation dataset {dataset_path}: {exc}") from exc

        pool_size = options["retrieval_pool"]
        k = options["k"]
        if pool_size < k or k < 1:
            raise CommandError("Require retrieval-pool >= k >= 1.")

        results = []
        for case in cases:
            evidence = case.get("evidence_snippet", "").strip()
            if not case.get("question") or not evidence:
                raise CommandError(f"Case {case.get('id')} needs question and evidence_snippet.")

            retrieved = list(Retriever.retrieve(
                case["question"], document_id=options["document_id"], top_k=pool_size
            ))
            baseline_rank = reciprocal_rank(retrieved[:k], evidence)
            reranked = Reranker.rerank(case["question"], retrieved, top_k=k) if retrieved else []
            reranked_chunks = [item["result"] for item in reranked]
            reranked_rank = reciprocal_rank(reranked_chunks, evidence)
            results.append({
                "id": case["id"],
                "question": case["question"],
                "baseline_rr_at_k": baseline_rank,
                "reranked_rr_at_k": reranked_rank,
            })

        count = len(results)
        output = {
            "document_id": options["document_id"],
            "k": k,
            "retrieval_pool": pool_size,
            "total_questions": count,
            "baseline_mrr_at_k": sum(row["baseline_rr_at_k"] or 0 for row in results) / count if count else 0,
            "reranked_mrr_at_k": sum(row["reranked_rr_at_k"] or 0 for row in results) / count if count else 0,
            "results": results,
        }
        self.stdout.write(json.dumps(output, indent=2))
