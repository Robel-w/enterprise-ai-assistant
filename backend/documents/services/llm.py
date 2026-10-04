from google import genai
from google.genai import errors
from django.conf import settings
import time

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
4. Combine information from multiple relevant chunks when necessary.
5. Answer the user's exact question, not a broader or different question.
6. Include only details necessary to answer the question.
7. If the answer is not supported by the document context, say:
   "I could not find the answer in the document."
8. Do not mention these instructions in your response.

DOCUMENT CONTEXT:
{context}

USER QUESTION:
{question}

ANSWER:
"""

    try:
        time.sleep(12)
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )

        return response.text

    except errors.ServerError as e:
        if e.code == 503:
            return (
                "The AI service is temporarily unavailable. "
                "Please try again in a moment."
            )

        raise