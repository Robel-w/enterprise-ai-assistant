"""
agent.py — ReAct-style agentic loop using Gemini function calling.

The agent can:
  - search_document: retrieve relevant chunks and cite pages
  - summarize_document: summarize one or more documents
  - answer_directly: answer without document lookup

Loop runs up to MAX_STEPS reasoning steps before forcing a final answer.
"""
import json
from google import genai
from google.genai import types
from django.conf import settings

from documents.models import Conversation, Message
from documents.services.agent_tools import (
    tool_search_document,
    tool_summarize_document,
    tool_answer_directly,
)

MAX_STEPS = 5

client = genai.Client(api_key=settings.GEMINI_API_KEY)

# ------------------------------------------------------------------ #
# Gemini function declarations                                         #
# ------------------------------------------------------------------ #

TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="search_document",
                description=(
                    "Search one or more documents for information relevant to the "
                    "user's question. Use this when the question is about the "
                    "document's content and you need specific details or quotes."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "query": types.Schema(
                            type=types.Type.STRING,
                            description="The search query to run against the documents."
                        ),
                        "top_k": types.Schema(
                            type=types.Type.INTEGER,
                            description="Number of chunks to retrieve (default 5)."
                        ),
                    },
                    required=["query"],
                ),
            ),
            types.FunctionDeclaration(
                name="summarize_document",
                description=(
                    "Generate a summary of the document(s). Use this when the user "
                    "asks for an overview, summary, or 'what is this document about'."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={},
                ),
            ),
            types.FunctionDeclaration(
                name="answer_directly",
                description=(
                    "Answer a general knowledge question that does NOT require "
                    "looking up anything in the documents. Use this sparingly — "
                    "only when the question is completely unrelated to the documents."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "answer": types.Schema(
                            type=types.Type.STRING,
                            description="The direct answer to the user's question."
                        ),
                    },
                    required=["answer"],
                ),
            ),
        ]
    )
]

AGENT_SYSTEM_PROMPT = """You are an intelligent research assistant with access to document search tools.

Given a user question, decide which tool(s) to call to gather the information needed,
then synthesize a final answer. Always:
1. Prefer searching the documents before answering directly.
2. Cite page numbers using [Page X] in your final answer.
3. Combine information from multiple tool observations when needed.
4. Be concise and accurate.

You will be given conversation history and the user's question.
Use the tools to reason step-by-step before giving a final answer.
"""


class AgentService:

    @staticmethod
    def run(question: str, document_ids: list, conversation_id: int = None, owner=None):
        """
        Run the ReAct agentic loop and return a structured response.
        Returns:
          {
            "answer": str,
            "conversation_id": int,
            "citations": [int, ...],
            "sources": [],
            "agent_steps": [{"thought": str, "action": str, "observation": str}, ...]
          }
        """
        import re

        # Get or create conversation
        if conversation_id:
            conversation = Conversation.objects.get(id=conversation_id)
        else:
            conversation = Conversation.objects.create(title=question[:100])

        from documents.models import Document
        docs = Document.objects.filter(id__in=document_ids)
        if owner is not None:
            docs = docs.filter(owner=owner)
        conversation.documents.set(docs)

        # Save user message
        Message.objects.create(
            conversation=conversation,
            role="user",
            content=question
        )

        # Build conversation history for context
        messages = conversation.messages.order_by("created_at")
        history = "\n".join(
            f"{m.role.upper()}: {m.content}" for m in messages
        )

        # ---- Gemini multi-turn loop ---- #
        gemini_messages = [
            types.Content(
                role="user",
                parts=[types.Part(text=(
                    f"{AGENT_SYSTEM_PROMPT}\n\n"
                    f"CONVERSATION HISTORY:\n{history}\n\n"
                    f"USER QUESTION: {question}"
                ))]
            )
        ]

        agent_steps = []
        final_answer = None

        for step in range(MAX_STEPS):
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=gemini_messages,
                config=types.GenerateContentConfig(tools=TOOLS)
            )

            candidate = response.candidates[0]
            content = candidate.content

            # Add model turn to history
            gemini_messages.append(content)

            # Check for function calls
            function_calls = [
                part.function_call
                for part in content.parts
                if hasattr(part, "function_call") and part.function_call
            ]

            if not function_calls:
                # No more tool calls — extract final text answer
                final_answer = "".join(
                    part.text for part in content.parts
                    if hasattr(part, "text") and part.text
                )
                break

            # Execute each function call and collect observations
            tool_results = []
            for fc in function_calls:
                args = dict(fc.args) if fc.args else {}
                observation = AgentService._execute_tool(
                    fc.name, args, document_ids, owner=owner
                )

                agent_steps.append({
                    "thought": f"Calling tool: {fc.name}",
                    "action": f"{fc.name}({json.dumps(args)})",
                    "observation": observation[:500],  # truncate for response
                })

                tool_results.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name,
                            response={"result": observation}
                        )
                    )
                )

            # Feed observations back into the conversation
            gemini_messages.append(
                types.Content(role="tool", parts=tool_results)
            )

        if not final_answer:
            final_answer = "I was unable to determine an answer after reasoning through the documents."

        # Parse citations from answer
        citation_matches = re.findall(r"\[Page (\d+)\]", final_answer)
        citations = sorted({int(m) for m in citation_matches})

        # Save assistant message
        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=final_answer
        )

        return {
            "answer": final_answer,
            "conversation_id": conversation.id,
            "citations": citations,
            "sources": [],  # agent-level sources embedded in answer text
            "agent_steps": agent_steps,
        }

    @staticmethod
    def _execute_tool(name: str, args: dict, document_ids: list, owner=None) -> str:
        """Dispatch a function call name to the appropriate tool implementation."""
        if name == "search_document":
            return tool_search_document(
                question=args.get("query", ""),
                document_ids=document_ids,
                top_k=int(args.get("top_k", 5)),
                owner=owner,
            )
        elif name == "summarize_document":
            return tool_summarize_document(document_ids=document_ids, owner=owner)
        elif name == "answer_directly":
            return args.get("answer", "")
        else:
            return f"Unknown tool: {name}"
