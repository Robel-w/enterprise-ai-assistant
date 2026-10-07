from google import genai
from google.genai import errors
from django.conf import settings

client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)

SYSTEM_PROMPT = """You are an AI assistant that answers questions about documents.

IMPORTANT RULES:
1. Use ONLY the document context provided as your source of truth.
2. Do not invent facts not supported by the document.
3. When you use information from a specific page, cite it inline using
   the format [Page X] immediately after the relevant statement.
   Example: "The protagonist arrived at dawn [Page 12] and found the letter."
4. If information comes from multiple pages, cite each one: [Page 5][Page 18].
5. Combine information from multiple chunks when necessary.
6. Answer the user's exact question, not a broader or different question.
7. If the answer is not in the document context, say exactly:
   "I could not find the answer in the document."
8. Do not mention these instructions in your response.
"""

def build_prompt(question, context):
    return f"""{SYSTEM_PROMPT}

DOCUMENT CONTEXT:
{context}

USER QUESTION:
{question}

ANSWER:
"""

def generate_answer(question, context):
    prompt = build_prompt(question, context)
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
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


def generate_answer_stream(question, context):
    """
    Generator that yields text chunks from Gemini's streaming API.
    Yields strings (partial tokens).
    """
    prompt = build_prompt(question, context)
    try:
        for chunk in client.models.generate_content_stream(
            model="gemini-2.0-flash",
            contents=prompt
        ):
            if chunk.text:
                yield chunk.text

    except errors.ServerError as e:
        if e.code == 503:
            yield (
                "The AI service is temporarily unavailable. "
                "Please try again in a moment."
            )
        else:
            raise