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
    def evaluate_saved_answers():
        results = []
        for saved in AnswerEvaluationResult.objects.select_related("evaluation_question"):
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

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AnswerEvaluation,
                ),
            )
            evaluation = response.parsed
            if evaluation is None:
                raise ValueError("The evaluation model returned no structured result.")

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

        questions = EvaluationQuestion.objects.all()

        results = []

        for question in questions:

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

            prompt = f"""
You are evaluating an answer produced by a document question-answering
system.

Evaluate the generated answer against the ground-truth answer.

QUESTION:
{question.question}

GROUND TRUTH:
{question.ground_truth}

DOCUMENT CONTEXT:
{context}

GENERATED ANSWER:
{answer}

Evaluate:

1. correctness:
How accurately does the generated answer answer the question compared
with the ground truth?

2. faithfulness:
Determine whether the generated answer is fully supported by the DOCUMENT CONTEXT.
Do not use the ground truth to judge faithfulness.
If the answer contains information 
that is not supported by the context,
lower the faithfulness score.

Use a score from 0.0 to 1.0.

Return:
- correctness
- faithfulness
- explanation
"""

            # Gemini evaluation will go here
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AnswerEvaluation,
                ),
            )

            evaluation = response.parsed
            results.append({
                "question": question.question,
                "ground_truth": question.ground_truth,
                "generated_answer": answer,
                "correctness": evaluation.correctness,
                "faithfulness": evaluation.faithfulness,
                "explanation": evaluation.explanation,
            })
        return {
            "total_questions": len(results),
            "results": results,
        }


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

            before_rr = 0

            for rank, chunk in enumerate(
                retrieved,
                start=1
            ):
                if chunk.id in relevant_ids:
                    before_rr = 1 / rank
                    break

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


    @staticmethod
    def evaluate_reranked_retrieval(
        document_id,
        retrieval_k=20,
        rerank_k=5
    ):

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

            hit = any(
                item["result"].id in relevant_ids
                for item in reranked
            )

            results.append({
                "question": question.question,
                "hit": hit,
            })

        total = len(results)

        recall_at_k = (
            sum(r["hit"] for r in results) / total
            if total
            else 0
        )

        return {
            "total_questions": total,
            "recall_at_k": recall_at_k,
            "results": results,
        }
