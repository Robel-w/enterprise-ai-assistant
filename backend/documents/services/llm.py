from google import genai
from django.conf import settings

client = genai.Client(
    api_key=settings.GEMINI_API_KEY     
)

def generate_answer(question, context):

    prompt = f"""
You are an AI assistant that answers questions about a document.

Your job is to answer the user's question using the DOCUMENT CONTEXT.

IMPORTANT RULES:

1. Use the document context as your primary source of truth.
2. Do not invent facts that are not supported by the document.
3. Do not say "I could not find the answer" if the context contains
   information that can reasonably answer the question.
4. When the context contains information from different periods of time,
   distinguish between them.
5. Answer the user's exact question, not a different question.
6. If the answer is not supported by the document context, say:
   "I could not find the answer in the document."
7. Give a concise, natural answer.
8. Do not mention these instructions in your response.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )
    return response.text