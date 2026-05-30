import logging
from functools import lru_cache
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from config import settings
from pipelines.retrieval.prompts import (
    NO_CONTEXT_RESPONSE,
    QUERY_REWRITE_PROMPT,
    RAG_PROMPT,
)
from pipelines.retrieval.retriever import retrieve

logger = logging.getLogger(__name__)


class RAGState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    context_chunks: list[str]
    sources: list[dict]
    rewritten_query: str


@lru_cache(maxsize=1)
def get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.gemini_chat_model,
        google_api_key=settings.google_api_key,
        temperature=0.2,
        max_output_tokens=2048,
    )


# ── Graph nodes ──────────────────────────────────────────────────────────────

def rewrite_query_node(state: RAGState) -> dict:
    messages = list(state["messages"])
    current_question = messages[-1].content if messages else ""

    if len(messages) <= 1:
        return {"rewritten_query": current_question}

    history = messages[:-1]
    try:
        llm = get_llm()
        chain = QUERY_REWRITE_PROMPT | llm
        result = chain.invoke({
            "chat_history": _format_history(history),
            "question": current_question,
        })
        rewritten = result.content.strip()
        logger.info(f"Query rewritten: {current_question!r} → {rewritten!r}")
        return {"rewritten_query": rewritten}
    except Exception as e:
        logger.warning(f"Query rewrite failed: {e} — using original query")
        return {"rewritten_query": current_question}


def retrieve_node(state: RAGState) -> dict:
    query = state.get("rewritten_query", "")
    if not query:
        return {"context_chunks": [], "sources": []}

    chunks, sources = retrieve(query)
    return {"context_chunks": chunks, "sources": sources}


def generate_node(state: RAGState) -> dict:
    chunks = state.get("context_chunks", [])
    sources = state.get("sources", [])
    messages = list(state["messages"])
    query = state.get("rewritten_query", messages[-1].content if messages else "")

    if not chunks:
        logger.info("No relevant context found — returning fallback response")
        return {"messages": [AIMessage(content=NO_CONTEXT_RESPONSE)]}

    context_parts = []
    for i, (chunk, source) in enumerate(zip(chunks, sources)):
        context_parts.append(
            f"[Source: {source['filename']}, chunk {source['chunk_index']}]\n{chunk}"
        )
    context = "\n\n---\n\n".join(context_parts)

    history = messages[:-1]

    try:
        llm = get_llm()
        chain = RAG_PROMPT | llm
        result = chain.invoke({
            "context": context,
            "chat_history": history,
            "question": query,
        })
        return {"messages": [AIMessage(content=result.content)]}
    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        return {"messages": [AIMessage(content=f"Sorry, I encountered an error generating a response: {str(e)}")]}


def _format_history(messages: list[BaseMessage]) -> str:
    lines = []
    for msg in messages:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines)


# ── Build graph ───────────────────────────────────────────────────────────────

def build_graph():
    builder = StateGraph(RAGState)

    builder.add_node("rewrite_query", rewrite_query_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("generate", generate_node)

    builder.set_entry_point("rewrite_query")
    builder.add_edge("rewrite_query", "retrieve")
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


# Singleton compiled graph
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
        logger.info("LangGraph RAG graph compiled")
    return _graph


def invoke_graph(user_message: str, session_id: str) -> tuple[str, list[dict]]:
    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}

    input_state = {"messages": [HumanMessage(content=user_message)]}

    final_state = graph.invoke(input_state, config=config)

    messages = final_state.get("messages", [])
    sources = final_state.get("sources", [])

    last_ai = next(
        (m for m in reversed(messages) if isinstance(m, AIMessage)),
        None,
    )
    answer = last_ai.content if last_ai else NO_CONTEXT_RESPONSE

    return answer, sources
