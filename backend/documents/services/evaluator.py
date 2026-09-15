from documents.services.retriever import Retriever
from documents.services.reranker import Reranker
from documents.models import EvaluationQuestion


class EvaluationService:

    @staticmethod
    def evaluate_reranking(document_id, retrieval_k=20, rerank_k=5):

        questions = EvaluationQuestion.objects.all()

        results = []

        for question in questions:

            retrieved = Retriever.retrieve(
                question.question,
                document_id=document_id,
                top_k=retrieval_k
            )

            reranked = Reranker.rerank(
                question.question,
                retrieved,
                top_k=rerank_k
            )

            relevant_ids = set(
                question.relevant_chunk_ids
            )

            # MRR before reranking
            before_rr = 0

            for rank, chunk in enumerate(
                retrieved,
                start=1
            ):
                if chunk.id in relevant_ids:
                    before_rr = 1 / rank
                    break

            # MRR after reranking
            after_rr = 0

            for rank, item in enumerate(
                reranked,
                start=1
            ):
                chunk = item["result"]

                if chunk.id in relevant_ids:
                    after_rr = 1 / rank
                    break

            results.append({
                "question": question.question,
                "before_rr": before_rr,
                "after_rr": after_rr,
            })

        total = len(results)

        before_mrr = (
            sum(r["before_rr"] for r in results) / total
            if total else 0
        )

        after_mrr = (
            sum(r["after_rr"] for r in results) / total
            if total else 0
        )

        return {
            "total_questions": total,
            "before_mrr": before_mrr,
            "after_mrr": after_mrr,
            "results": results,
        }