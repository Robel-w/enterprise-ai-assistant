import json
import time

from documents.services.retriever import Retriever
from documents.services.reranker import Reranker
from documents.models import (
    EvaluationQuestion,
    AnswerEvaluationResult
)
from pydantic import BaseModel
from documents.services.rag import RAGService
from documents.services.llm import client
from google.genai import types
from django.conf import settings
from evaluation.metrics import reciprocal_rank

class AnswerEvaluation(BaseModel):
    correctness: float
    faithfulness: float
    explanation: str


class EvaluationService:




    @staticmethod
    def generate_evaluation_answers(document_id, top_k=5):

        questions = EvaluationQuestion.objects.all()

        results = []

        for question in questions:
            existing = AnswerEvaluationResult.objects.filter(
                evaluation_question=question,
                document_id=document_id,
            ).first()
            if existing:
                results.append({
                    "id": existing.id,
                    "question": question.question,
                    "generated_answer": existing.generated_answer,
                    "cached": True,
                })
                continue

            rag_result = RAGService.ask(
                question=question.question,
                document_id=document_id,
                top_k=top_k
            )

            answer = rag_result["answer"]

            context = "\n\n".join(
                source["content"]
                for source in rag_result["sources"]
            )

            saved_result = AnswerEvaluationResult.objects.create(
                document_id=document_id,
                evaluation_question=question,
                generated_answer=answer,
                context=context
            )

            results.append({
                "id": saved_result.id,
                "question": question.question,
                "generated_answer": answer,
            })

        return {
            "total_questions": len(results),
            "results": results,
        }

    @staticmethod
    def evaluate_saved_answers(document_id=None):
        results = []
        saved_rows = AnswerEvaluationResult.objects.select_related("evaluation_question")
        if document_id is not None:
            saved_rows = saved_rows.filter(document_id=document_id)
        for saved in saved_rows:
            if saved.correctness is not None and saved.faithfulness is not None:
                results.append({
                    "id": saved.id,
                    "question": saved.evaluation_question.question,
                    "generated_answer": saved.generated_answer,
                    "correctness": saved.correctness,
                    "faithfulness": saved.faithfulness,
                    "explanation": saved.explanation,
                    "cached": True,
                })
                continue

            prompt = f"""
    You are evaluating an answer produced by a document question-answering system.

    Evaluate the generated answer using the ground-truth answer and
    the document context.

    QUESTION:
    {saved.evaluation_question.question}

    GROUND TRUTH:
    {saved.evaluation_question.ground_truth}

    GENERATED ANSWER:
    {saved.generated_answer}

    DOCUMENT CONTEXT:
    {saved.context}

    Evaluate:

    1. correctness:
    How accurately does the generated answer answer the question
    compared with the ground truth?

    2. faithfulness:
    Is the generated answer supported by the DOCUMENT CONTEXT?

    Important:
    - Do not use the ground truth to judge faithfulness.
    - Judge faithfulness only against the DOCUMENT CONTEXT.
    - Do not reward unsupported or invented information.

    Use a score from 0.0 to 1.0.

    Return:
    - correctness
    - faithfulness
    - explanation
    """

            last_error = None
            for attempt in range(3):
                try:
                    response = client.models.generate_content(
                        model=settings.GEMINI_MODEL,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=AnswerEvaluation,
                        ),
                    )
                    evaluation = response.parsed
                    if evaluation is None:
                        raise ValueError("The evaluation model returned no structured result.")
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt == 2:
                        raise
                    time.sleep(2 ** attempt)
            else:
                raise last_error

            saved.correctness = evaluation.correctness
            saved.faithfulness = evaluation.faithfulness
            saved.explanation = evaluation.explanation
            saved.save(update_fields=["correctness", "faithfulness", "explanation"])

            results.append({
                "id": saved.id,
                "question": saved.evaluation_question.question,
                "generated_answer": saved.generated_answer,
                "correctness": evaluation.correctness,
                "faithfulness": evaluation.faithfulness,
                "explanation": evaluation.explanation,
            })

        return {"total_questions": len(results), "results": results}


    @staticmethod
    def evaluate_answers(document_id, top_k=5):
        """Generate missing answers, then judge only rows without cached scores."""
        generated = EvaluationService.generate_evaluation_answers(document_id, top_k)
        judged = EvaluationService.evaluate_saved_answers(document_id=document_id)
        return {"total_questions": generated["total_questions"], "results": judged["results"]}


    @staticmethod
    def _evaluate_retrieval_cases(document_id, retrieval_k=20, rerank_k=5):
        dataset_path = settings.BASE_DIR / "evaluation" / "datasets" / "rag_test_cases.json"
        cases = json.loads(dataset_path.read_text(encoding="utf-8"))
        if retrieval_k < rerank_k or rerank_k < 1:
            raise ValueError("Require retrieval_k >= rerank_k >= 1.")

        results = []
        for case in cases:
            retrieved = list(Retriever.retrieve(
                case["question"], document_id=document_id, top_k=retrieval_k
            ))
            baseline_rr = reciprocal_rank(retrieved[:rerank_k], case["evidence_snippet"])
            reranked = Reranker.rerank(case["question"], retrieved, top_k=rerank_k) if retrieved else []
            reranked_rr = reciprocal_rank(
                [item["result"] for item in reranked], case["evidence_snippet"]
            )
            results.append({
                "id": case["id"],
                "question": case["question"],
                "before_rr": baseline_rr,
                "after_rr": reranked_rr,
            })
        total = len(results)
        return {
            "total_questions": total,
            "before_mrr": sum(row["before_rr"] or 0 for row in results) / total if total else 0,
            "after_mrr": sum(row["after_rr"] or 0 for row in results) / total if total else 0,
            "results": results,
        }

    @staticmethod
    def evaluate_reranking(document_id, retrieval_k=20, rerank_k=5):
        return EvaluationService._evaluate_retrieval_cases(document_id, retrieval_k, rerank_k)

    @staticmethod
    def evaluate_reranked_retrieval(document_id, retrieval_k=20, rerank_k=5):
        evaluation = EvaluationService._evaluate_retrieval_cases(document_id, retrieval_k, rerank_k)
        hits = [row["after_rr"] is not None and row["after_rr"] > 0 for row in evaluation["results"]]
        return {
            "total_questions": len(hits),
            "recall_at_k": sum(hits) / len(hits) if hits else 0,
            "results": [
                {"id": row["id"], "question": row["question"], "hit": hit}
                for row, hit in zip(evaluation["results"], hits)
            ],
        }
