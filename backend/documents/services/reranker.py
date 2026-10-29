from sentence_transformers import CrossEncoder


class Reranker:

    model = None

    @classmethod
    def _get_model(cls):
        if cls.model is None:
            cls.model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        return cls.model

    @staticmethod
    def rerank(query, results, top_k=5):
        pairs = [
            (query, result.content)
            for result in results
        ]

        scores = Reranker._get_model().predict(pairs)

        ranked_results = sorted(
            zip(results, scores),
            key=lambda x: x[1],
            reverse=True
        )

        return [
            {
                "result": result,
                "score": float(score)
            }
            for result, score in ranked_results[:top_k]
        ]
