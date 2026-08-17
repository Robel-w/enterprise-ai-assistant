# from django.conf import settings
# from openai import OpenAI

# client = OpenAI(
#     api_key=settings.OPENAI_API_KEY
# )

# def create_embedding(text:str) -> list[float]:
#     response = client.embeddings.create(
#         model="text-embedding-3-small",
#         input=text
#     )
#     return response.data[0].embedding


from sentence_transformers import SentenceTransformer

# This downloads a lightweight, highly efficient embedding model locally
model = SentenceTransformer("all-MiniLM-L6-v2")

def create_embedding(text: str) -> list[float]:
    # Generates a 384-dimensional vector completely free
    embedding_numpy = model.encode(text)
    return embedding_numpy.tolist()
