from google import genai
from django.conf import settings

client = genai.Client(
    api_key=settings.GEMINI_API_KEY     
)

def generate_answer(question, context):

    prompt = f"""
You are a document question-answering assistant.

Answer the user's question using ONLY the context provided below.

If the answer cannot be found in the context,
say that you could not find the answer in the document.

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